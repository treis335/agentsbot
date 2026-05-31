"""
agents/executor.py — Motor de execução de agentes com SOUL + MEMÓRIA REAL.

Carrega a personalidade (soul), injeta memória episódica e global no contexto,
e executa o loop de raciocínio com DeepSeek.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

from openai import AsyncOpenAI

from core.config import Config
from tools import TOOLS, execute_tool
from core.memory_hub import MemoryHub
from security.auditor import AuditLogger
from monitoring.metrics import MetricsCollector
from agents.verifier import verifier as tool_verifier
from agents.retry_policy import retry_policy

logger = logging.getLogger(__name__)


def RETRY_CONFIGS_MAX(tool_name: str) -> int:
    """Helper: devolve o max_retries configurado para uma ferramenta."""
    from agents.retry_policy import RETRY_CONFIGS
    cfg = RETRY_CONFIGS.get(tool_name, RETRY_CONFIGS["_default"])
    return cfg.max_retries

TOOL_SCHEMA = """
## FERRAMENTAS DISPONÍVEIS

Tens acesso a **{num_tools} ferramentas** para executar tarefas no servidor Linux.

| # | Ferramenta       | Parâmetros (obrigatórios a negrito) | Descrição                                               | Exemplo                                                       |
|---|------------------|-------------------------------------|---------------------------------------------------------|---------------------------------------------------------------|
| 1 | read_file        | **path** (str)                      | Lê conteúdo de um ficheiro                              | read_file(path="main.py")                                     |
| 2 | write_file       | **path** (str), **content** (str)   | Cria ou sobrescreve um ficheiro                         | write_file(path="main.py", content="print('oi')")             |
| 3 | list_files       | path (str, opcional)                | Lista ficheiros num diretório                           | list_files(path="src/")                                       |
| 4 | run_python       | **code** (str), timeout (int)       | Executa código Python no servidor                       | run_python(code="print('ola')")                               |
| 5 | run_shell        | **command** (str), timeout (int)    | Executa comando bash no servidor Linux                  | run_shell(command="git status")                               |
| 6 | git_status       | (nenhum)                            | Mostra estado do repositório Git                        | git_status()                                                  |
| 7 | git_commit_push  | **message** (str)                   | Faz git add, commit e push                              | git_commit_push(message="feat: adiciona login")               |
| 8 | create_agent     | **name** (str), **mission** (str)   | Cria novo agente no ecossistema                         | create_agent(name="X", mission="Faz Y")                       |
| 9 | search_github    | **query** (str), type (str)         | Pesquisa código ou issues no GitHub                     | search_github(query="login system")                           |
|10 | create_website   | **name** (str), **description** (str), pages (list), style (str) | Cria site completo (HTML/CSS/JS)     | create_website(name="Portfolio", description="Meu site")      |
|11 | add_page         | **site_name** (str), **page_name** (str), content (str) | Adiciona página a site existente       | add_page(site_name="Portfolio", page_name="sobre")            |
|12 | github_api       | **method** (str), **endpoint** (str), body (dict) | Chama GitHub API diretamente          | github_api(method="POST", endpoint="/user/repos")             |
|13 | web_search       | **query** (str)                     | Pesquisa informação na web                               | web_search(query="Python async patterns")                     |

**IMPORTANTE**: Usa SEMPRE os nomes e parâmetros exactos da tabela acima.

### REGRAS DE USO DAS FERRAMENTAS
1. **Nunca** chames uma ferramenta sem os argumentos obrigatórios
2. Se não tens um valor, descobre primeiro (lê, lista, pesquisa)
3. Prefere `run_python` a `run_shell` para lógica complexa
4. Usa `git_status()` antes de `git_commit_push()` para ver o que mudou
5. Lê o código antes de o alterar — contexto é essencial
6. Se uma ferramenta falhar, tenta 1 abordagem alternativa antes de desistir

### MODO AUTÓNOMO (sem supervisão humana)
Quando executas uma tarefa do backlog autónomo:
1. Segue o fluxo completo: (1) analisa, (2) executa, (3) valida, (4) commit
2. Reporta sempre o que fizeste de forma concisa no final
3. Não peças confirmação para executar acções — age directamente
4. Se algo falhar, tenta 1 alternativa antes de reportar erro
5. Preserva sempre o código existente — não apagues sem verificar
"""


class AgentExecutor:
    """
    Executor de um agente com personalidade (soul) e memória real.

    A memória episódica (experiências passadas) e global (decisões partilhadas)
    são injetadas no system prompt em cada execução.
    """

    def __init__(self, agent_name: str, agent_id: str = ""):
        self.config      = Config
        self.agent_name  = agent_name
        self.agent_id    = agent_id or agent_name
        self.soul        = self._load_soul()
        self.memory      = MemoryHub()
        self.memory.set_agent_id(self.agent_id)
        self.audit       = AuditLogger()
        self.metrics     = MetricsCollector()

        # Batch 6 — Inference Router: cliente escolhido dinamicamente por tarefa
        # O cliente estático DeepSeek mantém-se como fallback se o router falhar
        from inference.router import router as _router
        self._router = _router
        self._deepseek_client = AsyncOpenAI(
            api_key  = self.config.DEEPSEEK_API_KEY,
            base_url = self.config.DEEPSEEK_BASE_URL,
        )
        # Compatibilidade: self.client aponta para DeepSeek por defeito
        # mas run() vai usar o router para escolher dinamicamente
        self.client = self._deepseek_client

    def _load_soul(self) -> str:
        """Carrega a personalidade do agente: primeiro de souls/<name>.md,
        depois do agents.json, e por último um fallback genérico."""
        # 1) Ficheiro .md de soul
        soul_path = self.config.AGENTS_DIR / "souls" / f"{self.agent_name}.md"
        if soul_path.exists():
            content = soul_path.read_text(encoding="utf-8")
            logger.info(f"[{self.agent_name}] Soul carregado de .md ({len(content)} chars)")
            return content

        # 2) agents.json registry
        registry = self.config.AGENTS_FILE
        if registry.exists():
            try:
                agents = json.loads(registry.read_text(encoding="utf-8"))
                for a in agents:
                    if a.get("name", "").lower() == self.agent_name.lower():
                        soul = a.get("soul") or a.get("system_prompt", "")
                        if soul:
                            logger.info(f"[{self.agent_name}] Soul carregado de agents.json")
                            return soul
            except Exception as e:
                logger.warning(f"[{self.agent_name}] Erro ao ler agents.json: {e}")

        # 3) Fallback
        logger.warning(f"[{self.agent_name}] Soul n?o encontrado, usando fallback")
        return f"?s um agente chamado {self.agent_name}. Ages de forma aut?noma e eficiente."

    def _build_memory_context(self) -> str:
        """Constrói o contexto de memória para injetar no system prompt."""
        lines = ["\n## MEMÓRIA DO AGENTE\n"]

        # Memória episódica — últimas 5 experiências
        episodes = self.memory.get_episodes(self.agent_id, limit=5)
        if episodes:
            lines.append("### Experiências Recentes")
            for ep in episodes:
                d    = ep["data"]
                ts   = ep["timestamp"][:16]
                ok   = "[OK]" if d.get("success", True) else "[FAIL]"
                action = d.get("action", d.get("task", "?"))
                args_str = str(list(d.get("args", {}).keys())) if d.get("args") else "?"
                result = d.get("result", "")[:80]
                lines.append(f"{ok} [{ts}] {action}({args_str}) -> {result}")

        # Falhas recentes para evitar repetir erros
        failures = self.memory.get_episodes(self.agent_id, limit=3, only_failures=True)
        if failures:
            lines.append("\n### Erros Recentes (evita repetir)")
            for ep in failures:
                d = ep["data"]
                action = d.get("action", d.get("task", "?"))
                result = d.get("result", "")[:60]
                lines.append(f"[FAIL] {action}({d.get('args', {})}) -> {result}")

        # Memória global partilhada (via MemoryHub)
        try:
            decisions = self.memory.get_decisions(limit=5)
            if decisions:
                lines.append("\n### Decisões da Equipa (memória global)")
                for d in decisions:
                    lines.append(f"? [{d['timestamp'][:16]}] {d['agent']}: {d['decision'][:80]}")

            knowledge = self.memory.get_knowledge(limit=5)
            if knowledge:
                lines.append("\n### Conhecimento Partilhado")
                for k in knowledge:
                    topic = k['data'].get('topic', 'general')
                    content_val = k['data'].get('content', '')[:80]
                    lines.append(f"? {topic}: {content_val}")
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Mem?ria global indispon?vel: {e}")

                # Lições aprendidas (Batch 4)
        try:
            from memory.lesson_extractor import LessonExtractor
            lessons = LessonExtractor().get_lessons_for_agent(self.agent_id, limit=4)
            if lessons:
                lines.append("\n### Lições Aprendidas (evita estes erros)")
                for lesson in lessons:
                    lines.append(f"[RAPIDO] {lesson}")
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Li??es indispon?veis: {e}")

        return "\n".join(lines)

    def build_system_prompt(self, task: str) -> str:
        import platform
        memory_ctx = self._build_memory_context()

        # === CONTEXTO DE EXECUÇÃO ===
        repo_path = str(self.config.REPO_LOCAL_PATH)
        sandbox_on = getattr(self.config, "SANDBOX_ENABLED", False)
        runtime_lines = [
        "## CONTEXTO DE EXECUÇÃO (gerado automaticamente)",
        f"- Sistema: {platform.system()} {platform.release()} | Python {platform.python_version()}",
        f"- Projeto: {repo_path}",
        f"- Sandbox: {'ATIVO' if sandbox_on else 'DESATIVADO (execução direta no servidor)'}",
        "- Shell: bash Linux (ls, cat, python3, git) — NUNCA CMD Windows",
        "- NOTA: O utilizador está no Windows/PC — TU estás no servidor Linux",
        "- Comunicação com utilizador: via Telegram (já tratado automaticamente)",
        f"- Data/hora: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Agente: {self.agent_name} (ID: {self.agent_id})",
        ]
        runtime_ctx = "\n".join(runtime_lines)

        # === PROCEDIMENTOS RELEVANTES (HOW-TO) ===
        proc_ctx = ""
        try:
            from memory.procedural import ProceduralMemory
            proc_mem = ProceduralMemory()
            relevant_procs = proc_mem.get_relevant(task, limit=2)
            if relevant_procs:
                proc_ctx = "\n" + proc_mem.format_for_prompt(relevant_procs)
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Procedimentos indisponiveis: {e}")

        # === FALHAS SIMILARES (aprender com erros passados) ===
        failure_ctx = ""
        try:
            from memory.failure_memory import FailureMemory
            fm = FailureMemory(self.agent_id)
            similar = fm.get_similar_failures(task, limit=2)
            if similar:
                failure_ctx = "\n" + fm.format_for_prompt(similar)
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Failure memory indisponivel: {e}")

        # === INSTRUÇÕES DE EXECUÇÃO (obrigatório cumprir) ===
        exec_instructions = (
        "\n## INSTRUÇÕES DE EXECUÇÃO (cumpre sempre)\n"
        "1. LÊ A TAREFA e TODO o contexto fornecido antes de agir\n"
        "2. USA AS FERRAMENTAS para AGIR — não te limites a falar\n"
        "3. LÊ o código antes de o alterar — contexto é essencial\n"
        "4. VALIDA o resultado (testes, sintaxe, verificação)\n"
        "5. SE FALHAR, tenta abordagem alternativa (máx 3 tentativas)\n"
        "6. REPORTA o que fizeste no final\n"
        )

        # === MODO AUTÓNOMO (quando não há supervisão humana) ===
        auto_mode = (
        "\n## MODO AUTÓNOMO\n"
        "Estás a executar uma tarefa do backlog autónomo, sem supervisão humana.\n"
        "Segue o fluxo completo: (1) analisa, (2) executa, (3) valida, (4) faz commit.\n"
        "NÃO peças confirmação para executar ações. Age diretamente.\n"
        "Reporta o que fizeste de forma concisa no final.\n"
        )

        return (
        f"{self.soul}\n\n"
        f"{runtime_ctx}\n\n"
        f"{TOOL_SCHEMA}\n\n"
        f"{exec_instructions}\n"
        f"{auto_mode}\n"
        f"{memory_ctx}{proc_ctx}{failure_ctx}\n\n"
        f"## TAREFA ATUAL\n{task}"
        )

    async def run(
        self,
        task: str,
        context: Optional[list] = None,
        on_tool_call: Optional[Callable] = None,
        max_iterations: int = 30,
    ) -> tuple[str, list]:
        """
        Executa uma tarefa com o agente.

        Returns:
            (texto_final, contexto_atualizado)
        """
        system_prompt = self.build_system_prompt(task)

        if context:
            messages = list(context)
        else:
            messages = [{"role": "system", "content": system_prompt}]
            messages.append({
                "role": "user",
                "content": "Executa a tarefa indicada no system prompt. Usa as ferramentas disponíveis para agir de verdade."
            })

        # Batch 6 — escolher cliente via router (DeepSeek vs Ollama)
        try:
            active_client, active_model, routing = await self._router.get_client(
                task,
                context_size=len(str(messages)),
            )
            logger.debug(
                f"[{self.agent_name}] Router: {routing.provider.upper()} "
                f"{active_model} (score={routing.complexity_score:.2f}, {routing.complexity_label})"
            )
        except Exception as router_err:
            logger.warning(f"[{self.agent_name}] Router falhou, usando DeepSeek: {router_err}")
            active_client = self._deepseek_client
            active_model = "deepseek-chat"
            routing = None

        # Ollama não suporta tools — se local, desativar tool_use
        use_tools = (routing is None or not routing.use_local)

        for iteration in range(max_iterations):
            try:
                call_kwargs = dict(
                    model       = active_model,
                    messages    = messages,
                    temperature = 0.3,
                    max_tokens  = 2000,
                )
                if use_tools:
                    call_kwargs["tools"]       = TOOLS
                    call_kwargs["tool_choice"] = "auto"

                response = await active_client.chat.completions.create(**call_kwargs)
            except Exception as e:
                # Se Ollama falhou, tentar DeepSeek como fallback
                if routing and routing.use_local:
                    logger.warning(f"[{self.agent_name}] Ollama falhou ({e}), fallback DeepSeek")
                    self._router.invalidate_ollama_cache()
                    active_client = self._deepseek_client
                    active_model  = "deepseek-chat"
                    use_tools     = True
                    routing       = None
                    try:
                        response = await active_client.chat.completions.create(
                            model       = active_model,
                            messages    = messages,
                            tools       = TOOLS,
                            tool_choice = "auto",
                            temperature = 0.3,
                            max_tokens  = 2000,
                        )
                    except Exception as e2:
                        logger.error(f"[{self.agent_name}] Erro API (fallback): {e2}")
                        return f"Erro na API: {e2}", messages
                else:
                    logger.error(f"[{self.agent_name}] Erro API: {e}")
                    return f"Erro na API: {e}", messages

            msg    = response.choices[0].message
            finish = response.choices[0].finish_reason
            messages.append(msg.model_dump(exclude_none=True))

            # Registar uso de tokens
            if hasattr(response, "usage") and response.usage:
                self.metrics.track_token_usage(
                    self.agent_name, active_model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )

            if finish == "stop" or not msg.tool_calls:
                logger.info(f"[{self.agent_name}] Conclu?do em {iteration + 1} itera??o(?es)")
                # Registar conclusão na memória episódica
                self.memory.record(
                    action  = "task_complete",
                    args    = {"task": task[:100]},
                    result  = (msg.content or "Concluído")[:200],
                    success = True,
                    context = f"Itera??o {iteration + 1}",
                )
                # Registar na memória global (via MemoryHub)
                try:
                    self.memory.add_decision(
                        agent    = self.agent_name,
                        decision = f"Completou: {task[:80]}",
                        context  = (msg.content or "")[:200],
                    )
                except Exception:
                    pass
                return msg.content or "Tarefa concluída.", messages

            # Executar tool calls (com verificação e retry automático)
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                logger.info(f"[{self.agent_name}] Tool: {name}({list(args.keys())})")

                if on_tool_call:
                    await on_tool_call(name, args, "")

                # -- Loop de execução + verificação + retry ----------------
                retry_state = retry_policy.new_state(name)
                result      = None
                verified_ok = False

                while True:
                    start_time = asyncio.get_event_loop().time()
                    result     = await execute_tool(name, args)
                    elapsed    = (asyncio.get_event_loop().time() - start_time) * 1000

                    # Verificar resultado heuristicamente (zero API)
                    check = tool_verifier.verify(name, args, result)
                    retry_state.record_attempt(str(result), "" if check["ok"] else check["reason"])

                    if check["ok"]:
                        verified_ok = True
                        logger.debug(f"[{self.agent_name}] Verifica??o OK: {name}")
                        break

                    # Falhou verificação
                    logger.warning(
                        f"[{self.agent_name}] Verifica??o falhou: {name} ? {check['reason']}"
                    )

                    if not check["recoverable"] or not retry_state.can_retry:
                        logger.warning(
                            f"[{self.agent_name}] Sem retry para {name} "
                            f"(recuper?vel={check['recoverable']}, tentativas={retry_state.attempt})"
                        )
                        break

                    # Ajustar args e aguardar antes de retry
                    args = retry_policy.adjust_args(name, args, retry_state)
                    delay = retry_state.next_delay
                    logger.info(
                        f"[{self.agent_name}] Retry {retry_state.attempt}/{RETRY_CONFIGS_MAX(name)}"
                        f" para '{name}' em {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                # ---------------------------------------------------------

                success = verified_ok

                # Registar métricas
                self.metrics.track_tool_call(self.agent_name, name, elapsed, success)

                # Registar auditoria
                self.audit.log(
                    "tool_call",
                    agent      = self.agent_name,
                    tool       = name,
                    args       = args,
                    result     = str(result)[:200],
                    success    = success,
                    latency_ms = round(elapsed, 1),
                )

                # Registar memória episódica — aprende de cada tool call
                lesson = ""
                if not success:
                    lesson = retry_policy.format_retry_log(retry_state)
                self.memory.record(
                    action  = name,
                    args    = args,
                    result  = str(result)[:200],
                    success = success,
                    context = f"Tarefa: {task[:80]}, Itera??o {iteration + 1}",
                    lesson  = lesson,
                )

                if on_tool_call:
                    await on_tool_call(name, args, str(result)[:500])

                messages.append({
                    "role":        "tool",
                    "tool_call_id": tc.id,
                    "content":     str(result)[:2000],
                })

        logger.warning(f"[{self.agent_name}] Limite de {max_iterations} itera??es atingido")
        return "Limite de iterações atingido.", messages