"""
inference/offline_mode.py — Modo de sobrevivência local.

Quando a API DeepSeek está indisponível (sem créditos, sem internet,
quota esgotada), o sistema não para — activa o modo offline que:

  1. Detecta o tipo de erro (sem créditos vs sem internet vs timeout)
  2. Tenta Ollama local se disponível
  3. Se Ollama também não disponível: usa lógica determinística local
     - Executa tarefas com base em skills aprendidas
     - Usa o reflection_engine para recuperar soluções passadas
     - Usa a knowledge_base para responder sem LLM
     - Executa tarefas simples directamente (git, leitura de ficheiros)

  4. Notifica o owner uma vez quando entra em modo offline
  5. Verifica periodicamente se a API voltou
  6. Notifica quando sai do modo offline

Exemplo de o que consegue fazer sem API:
  - "git pull && git status"          → executa directamente
  - "lista os ficheiros em agents/"   → lê e retorna
  - "qual foi o último erro?"         → consulta loop_memory
  - "limpa logs antigos"              → executa com heurísticas
  - Qualquer skill aprendida          → aplica solução memorizada

O que NÃO consegue fazer sem API:
  - Gerar código novo complexo
  - Raciocinar sobre problemas novos
  - Brainstorming criativo
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class APIStatus(str, Enum):
    ONLINE          = "online"
    NO_CREDITS      = "no_credits"     # 402 / "insufficient balance"
    RATE_LIMITED    = "rate_limited"   # 429
    NO_INTERNET     = "no_internet"    # timeout / connection error
    AUTH_ERROR      = "auth_error"     # 401
    UNKNOWN_ERROR   = "unknown_error"


def classify_api_error(error: Exception) -> APIStatus:
    """Classifica o tipo de erro da API a partir da excepção."""
    err_str = str(error).lower()

    if any(w in err_str for w in ["402", "insufficient balance", "insufficient_quota",
                                    "no credits", "sem créditos", "out of credits"]):
        return APIStatus.NO_CREDITS

    if any(w in err_str for w in ["429", "rate limit", "too many requests"]):
        return APIStatus.RATE_LIMITED

    if any(w in err_str for w in ["401", "authentication", "invalid api key",
                                    "unauthorized", "api key"]):
        return APIStatus.AUTH_ERROR

    if any(w in err_str for w in ["timeout", "connection", "network", "refused",
                                    "unreachable", "dns", "no route"]):
        return APIStatus.NO_INTERNET

    return APIStatus.UNKNOWN_ERROR


class OfflineMode:
    """
    Gestor do modo offline — lógica local quando API indisponível.
    Singleton partilhado por todos os agentes.
    """

    # Quanto tempo esperar antes de re-tentar a API
    RETRY_INTERVALS = {
        APIStatus.NO_CREDITS:   3600,   # 1h — esperar recarregar
        APIStatus.RATE_LIMITED: 120,    # 2min
        APIStatus.NO_INTERNET:  60,     # 1min
        APIStatus.AUTH_ERROR:   0,      # Não retry — erro de configuração
        APIStatus.UNKNOWN_ERROR: 300,   # 5min
    }

    def __init__(self):
        self._status: APIStatus = APIStatus.ONLINE
        self._offline_since: Optional[float] = None
        self._last_retry: float = 0
        self._notified: bool = False
        self._telegram_bot = None
        self._owner_id: int = 0

    def set_notifier(self, bot, owner_id: int) -> None:
        self._telegram_bot = bot
        self._owner_id = owner_id

    @property
    def is_offline(self) -> bool:
        return self._status != APIStatus.ONLINE

    @property
    def status(self) -> APIStatus:
        return self._status

    def report_api_error(self, error: Exception) -> APIStatus:
        """
        Chamado quando uma chamada API falha.
        Classifica o erro e activa modo offline se necessário.
        """
        status = classify_api_error(error)

        if status != APIStatus.ONLINE:
            was_online = self._status == APIStatus.ONLINE
            self._status = status
            if was_online:
                self._offline_since = time.time()
                self._notified = False
                logger.warning(f"[OfflineMode] API indisponível: {status} — {str(error)[:80]}")
                # Notificar asyncio-safe
                asyncio.create_task(self._notify_offline(status))

        return status

    def report_api_success(self) -> None:
        """Chamado quando uma chamada API funciona — volta ao modo online."""
        if self._status != APIStatus.ONLINE:
            offline_duration = time.time() - (self._offline_since or time.time())
            logger.info(f"[OfflineMode] API voltou online (estava offline {offline_duration:.0f}s)")
            self._status = APIStatus.ONLINE
            self._offline_since = None
            self._notified = False
            asyncio.create_task(self._notify_online(offline_duration))

    def should_retry_api(self) -> bool:
        """True se já passou tempo suficiente para re-tentar a API."""
        if self._status == APIStatus.AUTH_ERROR:
            return False
        interval = self.RETRY_INTERVALS.get(self._status, 300)
        return time.time() - self._last_retry >= interval

    def mark_retry(self) -> None:
        self._last_retry = time.time()

    # ── Execução local (sem API) ───────────────────────────────────────────────

    async def execute_locally(self, task_desc: str, agent_name: str = "supervisor") -> str:
        """
        Executa tarefa sem API usando capacidades locais.
        Ordem de tentativa:
          1. Ollama local (se disponível)
          2. Skills memorizadas (reflection + knowledge base)
          3. Execução determinística directa
        """
        logger.info(f"[OfflineMode] Executar localmente: {task_desc[:60]}")

        # 1. Tentar Ollama
        ollama_result = await self._try_ollama(task_desc)
        if ollama_result:
            return ollama_result

        # 2. Tentar skills memorizadas
        memory_result = self._try_memory(task_desc)
        if memory_result:
            return memory_result

        # 3. Execução determinística
        return await self._execute_deterministic(task_desc)

    async def _try_ollama(self, task: str) -> Optional[str]:
        """
        Usa Ollama local com execução real de ferramentas.

        Ollama não suporta function calling nativo — em vez disso,
        pedimos ao modelo que gere acções em formato JSON estruturado,
        e nós executamo-las directamente com as ferramentas reais.
        """
        try:
            from inference.local_client import OllamaClient
            from core.config import Config

            ollama_url = getattr(Config, "OLLAMA_URL", "http://localhost:11434")
            local_model = getattr(Config, "LOCAL_MODEL", "qwen2.5-coder:7b")
            client = OllamaClient(base_url=ollama_url, timeout=120, model=local_model)

            # Verificar se Ollama está a correr (sem modelo obrigatório)
            try:
                import aiohttp as _aiohttp
                async with _aiohttp.ClientSession(timeout=_aiohttp.ClientTimeout(total=3)) as s:
                    async with s.get(f"{ollama_url}/api/tags") as r:
                        ollama_running = r.status == 200
                        if ollama_running:
                            data = await r.json()
                            available_models = [m["name"] for m in data.get("models", [])]
                        else:
                            available_models = []
            except Exception:
                logger.debug("[OfflineMode] Ollama não está a correr")
                return None

            if not ollama_running:
                logger.debug("[OfflineMode] Ollama não está disponível")
                return None

            # Encontrar o melhor modelo disponível
            best_model = await client.get_best_available_model()

            # Se nenhum modelo disponível, tentar pull do modelo mais leve
            if not available_models:
                logger.warning("[OfflineMode] Ollama sem modelos — a tentar pull de tinyllama:latest")
                pull_ok = await client.pull_model("tinyllama:latest")
                if not pull_ok:
                    logger.warning("[OfflineMode] Pull falhou — Ollama indisponível")
                    return None
                best_model = "tinyllama:latest"
                logger.info("[OfflineMode] tinyllama instalado com sucesso")

            local_model = best_model
            logger.info(f"[OfflineMode] Ollama disponível — a usar {local_model}")

            # Sistema prompt que instrui o modelo a gerar acções executáveis
            system_prompt = """És um agente autónomo de desenvolvimento de software.
Tens acesso a estas ferramentas locais (executa-as gerando JSON):
- write_file(path, content) — escreve ficheiro
- read_file(path) — lê ficheiro
- run_shell(command) — executa comando bash/cmd
- git_commit_push(message) — commit e push para GitHub

Quando receberes uma tarefa:
1. Analisa o que é necessário fazer
2. Gera as acções necessárias em formato JSON
3. Inclui sempre git_commit_push no final se fizeste alterações

Formato obrigatório para acções:
ACTIONS:
[
  {"tool": "write_file", "path": "caminho/ficheiro.py", "content": "conteúdo aqui"},
  {"tool": "run_shell", "command": "python -c 'print(1)'"},
  {"tool": "git_commit_push", "message": "feat: descrição do que foi feito"}
]

Se não há nada concreto a fazer, responde apenas com: NO_ACTION"""

            response = await client.chat.completions.create(
                model=local_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Tarefa: {task}"},
                ],
                max_tokens=2000,
                temperature=0.2,
            )

            raw = response.choices[0].message.content
            logger.debug(f"[OfflineMode] Ollama respondeu: {raw[:200]}")

            # Executar as acções geradas
            result = await self._execute_ollama_actions(raw, task)
            return result

        except Exception as e:
            logger.warning(f"[OfflineMode] Ollama erro: {e}")
            return None

    async def _execute_ollama_actions(self, ollama_response: str, task: str) -> str:
        """
        Interpreta a resposta do Ollama e executa as acções reais.
        Dá ao Ollama acesso efectivo a write_file, run_shell, git_commit_push.
        """
        import json, re

        if "NO_ACTION" in ollama_response:
            return f"Análise offline concluída: {ollama_response[:200]}"

        # Extrair bloco de acções JSON
        actions_match = re.search(r'ACTIONS:\s*(\[.*?\])', ollama_response, re.DOTALL)
        if not actions_match:
            # Sem acções estruturadas — retornar resposta como análise
            return f"[Ollama] {ollama_response[:500]}"

        try:
            actions = json.loads(actions_match.group(1))
        except json.JSONDecodeError:
            return f"[Ollama] Resposta gerada mas JSON inválido: {ollama_response[:300]}"

        results = []
        tools_used = []

        from tools.fs_tools import execute_tool

        for action in actions:
            tool = action.get("tool", "")
            if not tool:
                continue

            # Construir args para a ferramenta
            args = {k: v for k, v in action.items() if k != "tool"}

            try:
                logger.info(f"[OfflineMode] Ollama executa: {tool}({list(args.keys())})")
                import asyncio as _ai
                result = await execute_tool(tool, args)
                results.append(f"✅ {tool}: {str(result)[:150]}")
                tools_used.append(tool)
            except Exception as e:
                results.append(f"❌ {tool}: {e}")
                logger.warning(f"[OfflineMode] Erro em {tool}: {e}")

        summary = f"[Ollama+Tools] Executadas {len(tools_used)} acções: {', '.join(tools_used)}"
        if results:
            summary += "\n" + "\n".join(results[:5])

        logger.info(f"[OfflineMode] {summary[:200]}")
        return summary

    def _try_memory(self, task: str) -> Optional[str]:
        """Tenta resolver com conhecimento memorizado."""
        results = []

        # Consultar reflection engine
        try:
            from agents.reflection_engine import get_reflection_engine
            engine = get_reflection_engine()
            ctx = engine.get_prompt_context(task)
            if ctx and len(ctx) > 100:
                results.append(f"Com base em execuções anteriores:\n{ctx}")
        except Exception:
            pass

        # Consultar knowledge base
        try:
            from agents.collaboration.knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            entries = kb.query(task, limit=3)
            if entries:
                kb_lines = [e.to_prompt_line() for e in entries]
                results.append("Conhecimento relevante da equipa:\n" + "\n".join(kb_lines))
        except Exception:
            pass

        # Consultar loop memory
        try:
            from memory.loop_memory import get_loop_memory
            mem = get_loop_memory()
            ctx = mem.get_context_for_task(task)
            if ctx and len(ctx) > 50:
                results.append(ctx)
        except Exception:
            pass

        # _try_memory só fornece contexto — não executa tarefas
        # Devolver None para cair no _execute_deterministic
        return None

    async def _execute_deterministic(self, task: str) -> str:
        """
        Executa tarefas simples directamente sem LLM.
        Cobre: git, leitura de ficheiros, status do sistema.
        """
        task_lower = task.lower()
        results = []

        # Git operations
        if any(w in task_lower for w in ["git status", "git log", "git diff"]):
            try:
                import subprocess
                from core.config import Config
                cmd = "git status" if "status" in task_lower else \
                      "git log --oneline -10" if "log" in task_lower else "git diff --stat"
                proc = subprocess.run(cmd.split(), capture_output=True, text=True,
                                    cwd=str(Config.REPO_LOCAL_PATH), timeout=15)
                results.append(f"```\n{proc.stdout or proc.stderr}\n```")
            except Exception as e:
                results.append(f"Git: {e}")

        # Listar ficheiros
        elif any(w in task_lower for w in ["lista", "list", "ls", "dir", "ficheiros"]):
            try:
                from core.config import Config
                path = Config.REPO_LOCAL_PATH
                files = [f.name for f in sorted(path.iterdir())[:20]]
                results.append(f"Ficheiros em {path}:\n" + "\n".join(files))
            except Exception as e:
                results.append(f"Listagem: {e}")

        # Estado do backlog
        elif any(w in task_lower for w in ["backlog", "tarefa", "task", "pendente"]):
            try:
                import json
                bl = json.loads(Path("memory/backlog.json").read_text())
                bl = bl if isinstance(bl, list) else []
                pend = [t for t in bl if t.get("status") in ("pending", "")]
                done = sum(1 for t in bl if "done" in t.get("status", "").lower())
                results.append(
                    f"Backlog: {len(bl)} total | {len(pend)} pendentes | {done} concluídas\n"
                    + "\n".join(f"  - {t.get('title', t.get('id','?'))[:60]}" for t in pend[:5])
                )
            except Exception as e:
                results.append(f"Backlog: {e}")

        # Métricas do sistema
        elif any(w in task_lower for w in ["métricas", "metricas", "status", "estado", "saúde"]):
            try:
                from memory.loop_memory import get_loop_memory
                mem = get_loop_memory()
                stats = mem.stats()
                results.append(
                    f"Métricas locais:\n"
                    f"  Execuções: {stats.get('total_episodes', 0)}\n"
                    f"  Taxa sucesso: {stats.get('success_rate', 0)}%\n"
                    f"  Agente mais activo: {max(stats.get('by_agent', {}).items(), key=lambda x: x[1].get('total', 0), default=('?', {}))[0]}"
                )
            except Exception as e:
                results.append(f"Métricas: {e}")

        if not results:
            # Retornar marcador especial — o loop vai manter a tarefa como pending
            return "OFFLINE_NEEDS_API"

        return "[MODO OFFLINE] " + "\n\n".join(results)

    # ── Notificações ───────────────────────────────────────────────────────────

    async def _notify_offline(self, status: APIStatus) -> None:
        if self._notified or not self._telegram_bot or not self._owner_id:
            return
        self._notified = True

        msgs = {
            APIStatus.NO_CREDITS:   "💳 *Sem créditos DeepSeek*\n\nOs créditos da API esgotaram. O sistema entrou em modo offline — continua a trabalhar com Ollama local e memória acumulada.",
            APIStatus.RATE_LIMITED: "⏱ *Rate limit atingido*\n\nDemasiadas chamadas à API. A pausar 2 minutos e depois retoma automaticamente.",
            APIStatus.NO_INTERNET:  "📡 *Sem ligação à internet*\n\nAPI inacessível. O sistema vai usar Ollama local se disponível.",
            APIStatus.AUTH_ERROR:   "🔑 *Erro de autenticação DeepSeek*\n\nVerifica a DEEPSEEK_API_KEY no ficheiro `.env`.",
        }
        msg = msgs.get(status, f"⚠️ *API indisponível*\n\nStatus: {status}\nO sistema entrou em modo offline.")

        try:
            await self._telegram_bot.send_message(
                chat_id=self._owner_id,
                text=msg + "\n\n_O sistema continua a trabalhar com capacidades locais._",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    async def _notify_online(self, duration_s: float) -> None:
        if not self._telegram_bot or not self._owner_id:
            return
        mins = int(duration_s / 60)
        dur_str = f"{mins} minuto(s)" if mins > 0 else "menos de 1 minuto"
        try:
            await self._telegram_bot.send_message(
                chat_id=self._owner_id,
                text=f"✅ *API DeepSeek restaurada*\n\nEsteve offline {dur_str}. O sistema retoma operação normal.",
                parse_mode="Markdown",
            )
        except Exception:
            pass


# Singleton
_offline_mode = OfflineMode()

def get_offline_mode() -> OfflineMode:
    return _offline_mode

# Alias para compatibilidade
get_offline_manager = get_offline_mode
