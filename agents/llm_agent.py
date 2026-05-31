"""
agents/llm_agent.py — Agente LLM Autónomo Real

Este é o cérebro do sistema. Um único agente LLM que:
- Conversa naturalmente com o utilizador no Telegram
- Decide por si próprio quando usar ferramentas (sem iterar em loop infinito)
- Mantém memória de contexto persistente por utilizador
- Suporta DeepSeek (API externa) OU modo local com Anthropic
- Máximo 1-3 chamadas LLM por mensagem (não 30!)

Filosofia:
  - Chat normal -> 1 chamada LLM, resposta direta
  - Pedido de ação (criar ficheiro, git, etc.) -> 1 chamada LLM com tools, executa, responde
  - Tarefa complexa -> máximo 5 iterações com feedback real ao utilizador
"""
import asyncio
import json
import logging
import os
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# --- Prompt do sistema --------------------------------------------------------

def _build_system_prompt() -> str:
    import os as _os
    from core.config import Config as _Config
    repo_path   = str(_Config.REPO_LOCAL_PATH)
    github_repo = _os.getenv("GITHUB_REPO", "treis335/agentsbot")

    # Estado actual do loop autónomo — Telegram vê o que os agentes estão a fazer
    loop_context = ""
    try:
        from autonomous_loop import load_backlog, MEMORY_DIR
        backlog  = load_backlog()
        pending  = [t for t in backlog if t.get("status") == "pending"]
        done     = [t for t in backlog if t.get("status") == "done"]
        failed   = [t for t in backlog if t.get("status") == "failed"]

        loop_context = (
            "\n\n## ESTADO DO LOOP AUTÓNOMO\n"
            "- Tarefas pendentes: {}".format(len(pending))
        )
        if pending:
            loop_context += " -> " + ", ".join("'{}'".format(t.get("title", "?")) for t in pending[:3])
        loop_context += "\n- Concluídas: {} | Falhadas: {}".format(len(done), len(failed))

        log_path = MEMORY_DIR / "autonomous_log.md"
        if log_path.exists():
            recent = log_path.read_text(encoding="utf-8", errors="ignore").strip()
            last_lines = [l for l in recent.split("\n") if l.strip()][-4:]
            if last_lines:
                loop_context += "\n- Últimas acções:\n" + "\n".join("  " + l for l in last_lines)
    except Exception:
        pass

    return """És o Supervisor — líder do ecossistema agentsbot.

## IDENTIDADE
- Língua: Português de Portugal (sempre)
- Personalidade: Direto, proativo, orientado a ação. Fazes coisas, não apenas falas delas.
- És o líder da equipa: coordenas, delegas e garantes que o trabalho é feito.
- Pensas em termos de impacto, risco e prioridade.

## AMBIENTE REAL
- Corres num **servidor Linux remoto** (NÃO no Windows do utilizador)
- Projeto: {repo_path} | GitHub: {github_repo}
- Shell: bash Linux (ls, cat, python3, git) — NUNCA CMD Windows
- Caminhos Windows (C:\\Users\\...) não existem no servidor

## FERRAMENTAS (13 disponíveis)
Tens acesso às seguintes ferramentas para executar tarefas:

| Ferramenta       | Para quê                                        |
|------------------|-------------------------------------------------|
| read_file        | Ler conteúdo de ficheiros                       |
| write_file       | Criar/editar ficheiros                          |
| list_files       | Explorar diretórios                             |
| run_python       | Executar código Python                          |
| run_shell        | Executar comandos bash                          |
| git_status       | Ver estado do git                               |
| git_commit_push  | Commitar e fazer push para GitHub               |
| create_agent     | Criar novo agente especialista                  |
| search_github    | Pesquisar código/issues no GitHub               |
| create_website   | Criar sites completos (HTML/CSS/JS)             |
| add_page         | Adicionar página a site existente               |
| github_api       | Chamar GitHub API diretamente                   |
| web_search       | Pesquisar informação na web                     |

## REGRAS DE OURO
1. **Nunca apagar sem backup** — antes de modificar algo crítico, faz `git commit`
2. **Nunca expor credenciais** — API keys, tokens, passwords ficam em `.env`
3. **Nunca entrar em loop infinito** — se falha 3x seguidas, regista e escala
4. **Sempre documentar** — cada commit tem mensagem descritiva
5. **Nunca assumir — verificar** — confirma o estado actual antes de agir
6. **Estabilidade > velocidade** — um sistema lento mas estável vence um rápido mas frágil
7. **Confiar mas verificar** — delega mas monitoriza resultados

## FLUXO DE EXECUÇÃO

### 1. Receber Mensagem
- Lê a mensagem do utilizador
- Analisa contexto (memória, logs recentes)
- Decide se responde diretamente ou age (ferramentas)

### 2. Agir (se necessário)
- Escolhe a ferramenta certa para cada tarefa
- Executa e verifica o resultado
- Se falhar, tenta abordagem alternativa (máx 2x)

### 3. Responder
- Responde em Português PT claro
- Reporta o que fez e o resultado
- Se algo falhou, explica porquê

## CONTEXTO DO SISTEMA
{loop_context}arch, create_agent, search_github,
create_website, add_page, github_api.
Usa-as para agir — não te limites a falar sobre o que fazer.

## REGRAS DE CONDUTA
1. **Conversa normal** -> responde diretamente, sem tools
2. **Ações concretas** -> usa tools imediatamente (não perguntes "queres que faça?")
3. **Shell: sempre bash Linux** — comandos como ls, cat, python3, git
4. **Nunca inventes** — se não sabes, descobre (lê, pesquisa, executa)
5. **Foca-te APENAS em {github_repo}** — não toques noutros repositórios
6. **Lê antes de alterar** — contexto é essencial antes de modificar
7. **Português de Portugal sempre** — mesmo que te perguntem noutra língua
8. **Sê conciso** — respostas diretas, sem rodeios
9. **Se falhar, tenta de novo** — abordagem diferente antes de desistir
10. **Mantém contexto** — lembra-te do que foi dito antes
{loop_context}
""".format(repo_path=repo_path, github_repo=github_repo, loop_context=loop_context).format(repo_path=repo_path, github_repo=github_repo, loop_context=loop_context)
SYSTEM_PROMPT = _build_system_prompt()

# --- Schema de ferramentas (formato OpenAI/DeepSeek) -------------------------

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lê o conteúdo de um ficheiro do projeto.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Caminho do ficheiro"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Escreve conteúdo num ficheiro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lista ficheiros de um directório.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Executa um comando bash no servidor Linux.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Executa código Python e devolve o resultado.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Mostra o estado actual do repositório Git.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit_push",
            "description": "Faz commit e push de alterações para o GitHub.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "Mensagem do commit"}},
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Pesquisa informação na web.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_agent",
            "description": "Cria um novo agente no ecossistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "mission": {"type": "string"}
                },
                "required": ["name", "mission"]
            }
        }
    },
]

# --- Cliente LLM (DeepSeek com fallback) -------------------------------------

def _call_llm(messages: list, use_tools: bool = True, max_tokens: int = 1500) -> dict:
    """
    Router inteligente: Ollama local (GPU/CPU) OU DeepSeek (cloud).

    Prioridade:
      1. Se DEEPSEEK_API_KEY vazia → usa sempre Ollama (modo 100% local)
      2. Se Ollama disponível E tarefa simples (score < threshold) → Ollama
      3. Caso contrário → DeepSeek
      4. Fallback: se DeepSeek falhar → tenta Ollama; se Ollama falhar → DeepSeek

    Funciona com GPU (CUDA/Metal via Ollama) ou CPU — automaticamente.
    """
    from core.config import Config

    api_key  = getattr(Config, "DEEPSEEK_API_KEY", "")
    base_url = getattr(Config, "DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com"
    ollama_url  = getattr(Config, "OLLAMA_URL", "http://localhost:11434")
    local_model = getattr(Config, "LOCAL_MODEL", "qwen2.5-coder:7b")
    threshold   = float(getattr(Config, "ROUTING_THRESHOLD", "0.4"))

    # Decidir rota
    use_local = not api_key  # sem API key → sempre local

    if not use_local:
        # Score local de complexidade (zero API)
        try:
            task_text = next(
                (m["content"] if isinstance(m["content"], str) else ""
                 for m in reversed(messages) if m.get("role") == "user"), ""
            )
            from inference.complexity_scorer import score_task
            use_local = score_task(task_text).score < threshold
        except Exception:
            pass

    # Tentar Ollama
    if use_local:
        try:
            result = _call_ollama_sync(messages, ollama_url, local_model, max_tokens)
            _report_api_success()
            return result
        except Exception as e:
            logger.debug(f"[LLM] Ollama falhou: {e}")
            if not api_key:
                raise RuntimeError(
                    f"Sem DeepSeek API key e Ollama indisponível.\n"
                    f"Para usar localmente:\n"
                    f"  1. instala Ollama: https://ollama.com\n"
                    f"  2. corre: ollama serve\n"
                    f"  3. corre: ollama pull {local_model}\n"
                    f"  4. (opcional) adiciona ao .env: OLLAMA_URL=http://localhost:11434"
                )

    # Chamar DeepSeek
    payload = {
        "model": getattr(Config, "DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    if use_tools:
        payload["tools"]       = TOOLS_SCHEMA
        payload["tool_choice"] = "auto"

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read().decode("utf-8"))
        _report_api_success()
        return resp
    except Exception as api_err:
        _report_api_error(api_err)
        # Fallback para Ollama se DeepSeek falhar
        try:
            logger.warning(f"[LLM] DeepSeek falhou ({api_err}), fallback Ollama")
            return _call_ollama_sync(messages, ollama_url, local_model, max_tokens)
        except Exception:
            raise api_err  # re-raise o erro original se ambos falharem


def _call_ollama_sync(messages: list, base_url: str, model: str, max_tokens: int) -> dict:
    """
    Chama Ollama local (REST /api/chat).
    Funciona com GPU (CUDA/Metal) ou CPU automaticamente — o Ollama detecta.
    Retorna dict no formato OpenAI para compatibilidade.
    """
    # Ollama não suporta tool_use — remover se presente
    clean_messages = [
        {"role": m["role"], "content": m["content"] if isinstance(m["content"], str)
         else str(m.get("content",""))}
        for m in messages
        if m.get("role") in ("system", "user", "assistant")
        and m.get("content")
    ]

    payload = {
        "model": model,
        "messages": clean_messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"{base_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = json.loads(r.read().decode("utf-8"))

    content = raw.get("message", {}).get("content", "")
    if not content:
        raise ValueError("Ollama retornou resposta vazia")

    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage":   {"prompt_tokens": raw.get("prompt_eval_count", 0),
                    "completion_tokens": raw.get("eval_count", 0)},
        "model":   model,
        "_source": "ollama",
    }


def _report_api_success() -> None:
    try:
        from inference.offline_mode import get_offline_mode
        get_offline_mode().report_api_success()
    except Exception:
        pass


def _report_api_error(e: Exception) -> None:
    try:
        from inference.offline_mode import get_offline_mode
        get_offline_mode().report_api_error(e)
    except Exception:
        pass


# --- Memória de conversa persistente -----------------------------------------

def _history_path(user_id: int) -> Path:
    try:
        from core.config import Config
        return Config.MEMORY_DIR / "conversations" / f"tg_{user_id}.json"
    except Exception:
        return Path(__file__).parent.parent / "memory" / "conversations" / f"tg_{user_id}.json"


def load_history(user_id: int) -> list:
    """Carrega histórico de conversa (últimas 30 mensagens)."""
    path = _history_path(user_id)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data[-30:]
    except Exception as e:
        logger.debug(f"[LLMAgent] Erro ao carregar hist?rico {user_id}: {e}")
    return []


def save_history(user_id: int, history: list) -> None:
    """Guarda histórico de conversa (máximo 50 entradas)."""
    path = _history_path(user_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(history[-50:], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"[LLMAgent] Erro ao guardar hist?rico {user_id}: {e}")


def clear_history(user_id: int) -> None:
    """Limpa o histórico de conversa."""
    path = _history_path(user_id)
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


# --- Executor de ferramentas --------------------------------------------------

async def _run_tool(name: str, args: dict) -> str:
    """Executa uma ferramenta e retorna o resultado como string."""
    try:
        from tools import execute_tool
        result = await execute_tool(name, args)
        return str(result)[:3000]
    except Exception as e:
        logger.error(f"[LLMAgent] Erro na ferramenta {name}: {e}")
        return f"Erro ao executar {name}: {e}"


# --- Agente Principal ---------------------------------------------------------

class LLMAgent:
    """
    Agente LLM autónomo com:
    - Memória de conversa persistente por utilizador
    - Uso inteligente de ferramentas (só quando necessário)
    - Suporte a agent_name para carregar soul específico
    - Máximo 50 iterações de tools por mensagem
    """

    MAX_TOOL_ITERATIONS = 50

    def __init__(self, agent_name: str = "supervisor"):
        self.agent_name = agent_name
        self._history = []
        self._system = self._build_system_prompt()

    def _load_soul(self) -> str:
        """Carrega o soul do agente pelo nome. Fallback para SYSTEM_PROMPT global."""
        from core.config import Config
        soul_path = Config.AGENTS_DIR / "souls" / f"{self.agent_name}.md"
        if soul_path.exists():
            soul = soul_path.read_text(encoding="utf-8").strip()
            logger.info(f"[LLMAgent] Soul carregado: {self.agent_name}")
            return soul
        # Fallback: supervisor soul ou prompt global
        fallback = Config.AGENTS_DIR / "souls" / "supervisor.md"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8").strip()
        return SYSTEM_PROMPT

    def _build_system_prompt(self) -> str:
        """Constrói o system prompt com soul do agente + contexto actual."""
        import platform
        from core.config import Config
        soul = self._load_soul()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Tools disponíveis
        tools_list = (
            "\n\n## FERRAMENTAS DISPONÍVEIS\n"
            "- write_file(path, content): Criar/sobrescrever ficheiros\n"
            "- read_file(path): Ler conteúdo de ficheiros\n"
            "- list_files(path): Listar ficheiros num diretório\n"
            "- run_python(code): Executar código Python\n"
            "- run_shell(command): Executar comandos bash Linux\n"
            "- git_status(): Ver estado do repositório\n"
            "- git_commit_push(message): Commit + push\n"
            "- create_agent(name, mission): Criar novo agente\n"
            "- web_search(query): Pesquisar na web\n"
            "\nUsa estas ferramentas para AGIR - não apenas falar sobre o que fazer."
        )
        
        runtime = (
            f"\n\n## CONTEXTO DE EXECU??O\n"
            f"- Agente: {self.agent_name}\n"
            f"- Data/hora: {now}\n"
            f"- Sistema: {platform.system()} Linux servidor\n"
            f"- Projecto: {Config.REPO_LOCAL_PATH}\n"
            f"- Shell: bash (ls, cat, python3, git - nunca CMD Windows)\n"
            f"- O utilizador está no Windows/PC - TU estás no servidor Linux\n"
        )
        
        # Instruções de execução
        exec_instructions = (
            "\n## INSTRUÇÕES DE EXECUÇÃO\n"
            "1. Lê a tarefa e age - usa as ferramentas disponíveis\n"
            "2. Lê o código antes de o alterar\n"
            "3. Verifica o resultado (testes, validação)\n"
            "4. Se falhar, tenta alternativa antes de desistir\n"
            "5. Reporta o que fizeste de forma concisa\n"
        )
        
        return soul + tools_list + runtime + exec_instructions

    def _check_and_reset_if_looping(self) -> bool:
        """Detecta se o agente entrou em loop sobre 'preso no docker' e limpa o histórico."""
        if len(self._history) < 4:
            return False
        recent = " ".join(
            m.get("content", "") for m in self._history[-6:]
            if m.get("role") == "assistant"
        ).lower()
        loop_signals = ["preso no docker", "preso dentro do", "não consigo sair", "estou dentro do container", "flag partida"]
        if sum(1 for s in loop_signals if s in recent) >= 2:
            import logging
            logging.getLogger(__name__).warning("[LLMAgent] Loop detectado — a limpar histórico")
            self._history = []
            return True
        return False

    async def chat(
        self,
        user_id: int,
        user_message: str,
        on_progress: Optional[Callable] = None,
    ) -> str:
        """
        Processa uma mensagem do utilizador.
        
        Args:
            user_id: ID do utilizador Telegram
            user_message: Mensagem enviada pelo utilizador
            on_progress: Callback async(texto) para enviar updates de progresso
            
        Returns:
            Resposta final do agente como string
        """
        # Modo autónomo (user_id=0) — sem histórico de conversa, foco total na tarefa
        is_autonomous = (user_id == 0)

        if is_autonomous:
            history = []
        else:
            history = load_history(user_id)
            # Detectar e limpar loop de "preso no docker"
            self._history = history
            if self._check_and_reset_if_looping():
                history = []
                save_history(user_id, [])
            # Limitar histórico a 10 mensagens
            history = history[-10:]

        # System prompt ligeiramente diferente em modo autónomo
        if is_autonomous:
            system = self._build_system_prompt() + (
                "\n\n## MODO AUTÓNOMO\n"
                "Estás a executar uma tarefa do backlog autónomo, sem supervisão humana. "
                "Executa a tarefa completamente usando as ferramentas disponíveis. "
                "Reporta o que fizeste de forma concisa. Não peças confirmação."
            )
        else:
            system = self._build_system_prompt()

        # Construir mensagens para o LLM
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        tools_used = []

        for iteration in range(self.MAX_TOOL_ITERATIONS + 1):
            try:
                # Chamar LLM
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: _call_llm(messages, use_tools=True)
                )
            except RuntimeError as e:
                # API key não configurada
                reply = f"[!] {e}\n\nConfigure a DEEPSEEK_API_KEY no ficheiro .env."
                self._update_history(history, user_message, reply, user_id)
                return reply
            except Exception as e:
                logger.error(f"[LLMAgent] Erro API iteração {iteration}: {e}")

                # Detectar e gerir modo offline
                try:
                    from inference.offline_mode import get_offline_mode
                    offline = get_offline_mode()
                    api_status = offline.report_api_error(e)
                    logger.warning(f"[LLMAgent] API status: {api_status}")

                    if iteration == 0:
                        # Chat directo via Ollama (mais rápido que execute_locally)
                        local_result = await offline.chat_with_ollama(
                            messages=messages,
                            system=self._system,
                        )

                        if not local_result:
                            local_result = (
                                f"⚠️ API DeepSeek sem créditos e Ollama indisponível.\n"
                                f"O Ollama está instalado? Corre: ollama serve\n"
                                f"Modelo instalado? Corre: ollama pull qwen2.5-coder:7b"
                            )
                        self._update_history(history, user_message, local_result, user_id)
                        return local_result
                except Exception as offline_err:
                    logger.debug(f"[OfflineMode] Erro: {offline_err}")

                if iteration == 0:
                    return f"❌ Erro ao contactar o LLM: {e}\nVerifique DEEPSEEK_API_KEY e ligação à internet."
                break

            choice = response.get("choices", [{}])[0]
            msg = choice.get("message", {})
            finish_reason = choice.get("finish_reason", "stop")

            # Sem tool calls -> resposta final
            if finish_reason == "stop" or not msg.get("tool_calls"):
                reply = msg.get("content") or "Tarefa concluída."
                
                # Adicionar resumo das ferramentas usadas
                if tools_used:
                    summary = f"\n\n[FIX] *Opera??es realizadas:* {', '.join(tools_used)}"
                    reply += summary

                self._update_history(history, user_message, msg.get("content", reply), user_id)
                return reply

            # Processar tool calls
            messages.append({
                "role": "assistant",
                "content": msg.get("content"),
                "tool_calls": msg["tool_calls"]
            })

            for tc in msg["tool_calls"]:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_args = {}

                # Notificar utilizador sobre o que está a fazer
                if on_progress and iteration == 0:
                    await on_progress(f"[FIX] A executar: `{tool_name}`...")

                logger.info(f"[LLMAgent] Tool: {tool_name}({list(tool_args.keys())})")
                result = await _run_tool(tool_name, tool_args)

                tools_used.append(tool_name)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        # Atingiu o limite de iterações — pedir resumo SEM ferramentas
        logger.warning(f"[LLMAgent] Limite de itera??es atingido para user {user_id}")
        messages.append({
            "role": "user",
            "content": (
                "Atingiste o limite de operações para esta mensagem. "
                "Em 2 frases: o que fizeste e o que ficou por fazer (se algo ficou)."
            )
        })
        try:
            final_resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _call_llm(messages, use_tools=False, max_tokens=300)
            )
            reply = final_resp["choices"][0]["message"].get("content", "")
            if not reply:
                reply = f"Conclu?: {', '.join(set(tools_used))}."
        except Exception:
            reply = f"Opera??es realizadas: {', '.join(set(tools_used))}."

        # Guardar histórico com a resposta final (não o estado incompleto)
        self._update_history(history, user_message, reply, user_id)
        return reply

    def _update_history(self, history: list, user_msg: str, assistant_reply: str, user_id: int):
        """Actualiza e guarda o histórico."""
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_reply})
        save_history(user_id, history)


# --- Singleton global ---------------------------------------------------------

_agent_instance: Optional[LLMAgent] = None


def get_agent() -> LLMAgent:
    """Retorna a instância singleton do agente."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = LLMAgent()
        logger.info("[LLMAgent] Agente LLM inicializado.")
    return _agent_instance
