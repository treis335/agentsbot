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
        """Tenta usar Ollama local se disponível."""
        try:
            from inference.local_client import OllamaClient
            from core.config import Config

            ollama_url = getattr(Config, "OLLAMA_URL", "http://localhost:11434")
            client = OllamaClient(base_url=ollama_url, timeout=60)

            if not await client.is_available():
                return None

            models = await client.list_models()
            if not models:
                return None

            # Usar o primeiro modelo disponível
            model = models[0]
            logger.info(f"[OfflineMode] Usando Ollama: {model}")

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": (
                        "És um agente de sistema autónomo a trabalhar em modo offline. "
                        "Sem acesso à internet. Usa apenas o que sabes e as ferramentas locais. "
                        "Sê directo e executa o que conseguires."
                    )},
                    {"role": "user", "content": task},
                ],
                max_tokens=1000,
                temperature=0.3,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.debug(f"[OfflineMode] Ollama indisponível: {e}")
            return None

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

        if results:
            return (
                f"[MODO OFFLINE — sem API] Resposta baseada em conhecimento local:\n\n"
                + "\n\n".join(results)
                + "\n\n⚠️ API indisponível. Para tarefas complexas, aguardar restauração."
            )
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
            return (
                f"[MODO OFFLINE] API DeepSeek indisponível ({self._status}).\n"
                f"Tarefa requer raciocínio LLM — não é possível executar localmente.\n"
                f"Tarefa guardada no backlog para quando a API voltar."
            )

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
