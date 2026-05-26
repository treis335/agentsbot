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
from memory.episodica import EpisodicMemory
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

| Ferramenta       | Argumentos Obrigatórios          | Exemplo                                               |
|------------------|----------------------------------|-------------------------------------------------------|
| write_file       | path (str), content (str)        | write_file(path="main.py", content="print('oi')")     |
| read_file        | path (str)                       | read_file(path="main.py")                             |
| list_files       | path (str, opcional)             | list_files(path="src/")                               |
| run_python       | code (str)                       | run_python(code="print('ola')")                       |
| run_shell        | command (str)                    | run_shell(command="git status")                       |
| git_status       | (sem argumentos)                 | git_status()                                          |
| git_commit_push  | message (str)                    | git_commit_push(message="feat: adiciona x")           |
| create_agent     | name (str), mission (str)        | create_agent(name="X", mission="Faz Y")               |
| search_github    | query (str)                      | search_github(query="python asyncio")                 |
| web_search       | query (str)                      | web_search(query="ultimas novidades IA")              |

REGRA: Nunca chames uma ferramenta sem os argumentos obrigatórios.
Se não tens o valor, descobre primeiro (lê, lista, pesquisa).
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
        self.memory      = EpisodicMemory(self.agent_id)
        self.audit       = AuditLogger()
        self.metrics     = MetricsCollector()
        self.client      = AsyncOpenAI(
            api_key  = self.config.DEEPSEEK_API_KEY,
            base_url = self.config.DEEPSEEK_BASE_URL,
        )

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
        logger.warning(f"[{self.agent_name}] Soul não encontrado, usando fallback")
        return f"És um agente chamado {self.agent_name}. Ages de forma autónoma e eficiente."

    def _build_memory_context(self) -> str:
        """Constrói o contexto de memória para injetar no system prompt."""
        lines = ["\n## MEMÓRIA DO AGENTE\n"]

        # Memória episódica — últimas 5 experiências
        recent = self.memory.get_recent(5)
        if recent:
            lines.append("### Experiências Recentes")
            for ep in recent:
                e    = ep["episode"]
                ts   = ep["timestamp"][:16]
                ok   = "✅" if ep["success"] else "❌"
                lines.append(f"{ok} [{ts}] {e['action']}({list(e['args'].keys())}) → {e['result'][:80]}")

        # Falhas recentes para evitar repetir erros
        failures = self.memory.get_failures(3)
        if failures:
            lines.append("\n### Erros Recentes (evita repetir)")
            for ep in failures:
                e = ep["episode"]
                lines.append(f"❌ {e['action']}({e['args']}) → {e['result'][:60]}")

        # Memória global partilhada
        try:
            from memory.global_memory import GlobalMemory
            gm = GlobalMemory()

            decisions = gm.get_decisions(5)
            if decisions:
                lines.append("\n### Decisões da Equipa (memória global)")
                for d in decisions:
                    lines.append(f"• [{d['timestamp'][:16]}] {d['agent']}: {d['decision'][:80]}")

            knowledge = gm.get_knowledge()
            if knowledge:
                lines.append("\n### Conhecimento Partilhado")
                for k in knowledge[-5:]:
                    lines.append(f"• {k['topic']}: {k['content'][:80]}")
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Memória global indisponível: {e}")

        return "\n".join(lines)

    def build_system_prompt(self, task: str) -> str:
        """Constrói o system prompt completo: soul + memória + tools + tarefa."""
        memory_ctx = self._build_memory_context()
        return (
            f"{self.soul}\n\n"
            f"{TOOL_SCHEMA}\n\n"
            f"{memory_ctx}\n\n"
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

        for iteration in range(max_iterations):
            try:
                response = await self.client.chat.completions.create(
                    model       = "deepseek-chat",
                    messages    = messages,
                    tools       = TOOLS,
                    tool_choice = "auto",
                    temperature = 0.3,
                    max_tokens  = 2000,
                )
            except Exception as e:
                logger.error(f"[{self.agent_name}] Erro API: {e}")
                return f"Erro na API: {e}", messages

            msg    = response.choices[0].message
            finish = response.choices[0].finish_reason
            messages.append(msg.model_dump(exclude_none=True))

            # Registar uso de tokens
            if hasattr(response, "usage") and response.usage:
                self.metrics.track_token_usage(
                    self.agent_name, "deepseek-chat",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )

            if finish == "stop" or not msg.tool_calls:
                logger.info(f"[{self.agent_name}] Concluído em {iteration + 1} iteração(ões)")
                # Registar conclusão na memória episódica
                self.memory.record(
                    action  = "task_complete",
                    args    = {"task": task[:100]},
                    result  = (msg.content or "Concluído")[:200],
                    success = True,
                    context = f"Iteração {iteration + 1}",
                )
                # Registar na memória global
                try:
                    from memory.global_memory import GlobalMemory
                    GlobalMemory().add_decision(
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

                # ── Loop de execução + verificação + retry ────────────────
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
                        logger.debug(f"[{self.agent_name}] Verificação OK: {name}")
                        break

                    # Falhou verificação
                    logger.warning(
                        f"[{self.agent_name}] Verificação falhou: {name} — {check['reason']}"
                    )

                    if not check["recoverable"] or not retry_state.can_retry:
                        logger.warning(
                            f"[{self.agent_name}] Sem retry para {name} "
                            f"(recuperável={check['recoverable']}, tentativas={retry_state.attempt})"
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
                # ─────────────────────────────────────────────────────────

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
                    context = f"Tarefa: {task[:80]}, Iteração {iteration + 1}",
                    lesson  = lesson,
                )

                if on_tool_call:
                    await on_tool_call(name, args, str(result)[:500])

                messages.append({
                    "role":        "tool",
                    "tool_call_id": tc.id,
                    "content":     str(result)[:2000],
                })

        logger.warning(f"[{self.agent_name}] Limite de {max_iterations} iterações atingido")
        return "Limite de iterações atingido.", messages