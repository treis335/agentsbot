"""
agents/executor.py — Motor de execucao de agentes com suporte a SOUL.

Carrega a personalidade (soul) do ficheiro .md, combina com as
ferramentas disponiveis, e executa o loop de raciocinio do agente.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Optional

from openai import AsyncOpenAI

from core.config import Config
from tools import TOOLS, execute_tool
from memory.episodica import EpisodicMemory
from security.auditor import AuditLogger
from monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

# Template de ferramentas injetado no system prompt
TOOL_SCHEMA = """
## FERRAMENTAS DISPONIVEIS

| Ferramenta       | Argumentos Obrigatorios          | Exemplo                                              |
|------------------|----------------------------------|------------------------------------------------------|
| write_file       | path (str), content (str)        | write_file(path="main.py", content="print('oi')")    |
| read_file        | path (str)                       | read_file(path="main.py")                            |
| list_files       | path (str, opcional)             | list_files(path="src/")                              |
| run_python       | code (str)                       | run_python(code="print('ola')")                      |
| run_shell        | command (str)                    | run_shell(command="dir")                             |
| git_status       | (sem argumentos)                 | git_status()                                         |
| git_commit_push  | message (str)                    | git_commit_push(message="feat: adiciona x")          |
| create_agent     | name (str), mission (str)        | create_agent(name="X", mission="Faz Y")              |
| search_github    | query (str)                      | search_github(query="python asyncio")                |
| web_search       | query (str)                      | web_search(query="ultimas novidades IA")             |

REGRA: Nunca chames uma ferramenta sem os argumentos obrigatorios.
Se nao tens o valor, descobre primeiro (le, lista, pesquisa).
"""


class AgentExecutor:
    """
    Executor de um agente com personalidade (soul).

    Uso:
        executor = AgentExecutor("developer")
        resultado, contexto = await executor.run("Implementa uma funcao...")
    """

    def __init__(self, agent_name: str, agent_id: str = ""):
        self.config = Config
        self.agent_name = agent_name
        self.agent_id = agent_id or agent_name
        self.soul = self._load_soul()
        self.memory = EpisodicMemory(self.agent_id)
        self.audit = AuditLogger()
        self.metrics = MetricsCollector()
        self.client = AsyncOpenAI(
            api_key=self.config.DEEPSEEK_API_KEY,
            base_url=self.config.DEEPSEEK_BASE_URL,
        )

    def _load_soul(self) -> str:
        """Carrega a personalidade do agente do ficheiro .md."""
        soul_path = self.config.AGENTS_DIR / "souls" / f"{self.agent_name}.md"
        if soul_path.exists():
            content = soul_path.read_text(encoding="utf-8")
            logger.info(f"[{self.agent_name}] Soul carregado: {len(content)} chars")
            return content
        logger.warning(f"[{self.agent_name}] Soul nao encontrado: {soul_path}")
        return f"És um agente chamado {self.agent_name}. Ages de forma autonoma."

    def build_system_prompt(self, task: str) -> str:
        """Constrói o system prompt completo com soul + tools + task."""
        return f"{self.soul}\n\n{TOOL_SCHEMA}\n\nTAREFA ATUAL:\n{task}"

    async def run(self, task: str, context: Optional[list] = None,
                  on_tool_call: Optional[Callable] = None,
                  max_iterations: int = 30) -> tuple[str, list]:
        """
        Executa uma tarefa com o agente.

        Args:
            task: Descricao da tarefa
            context: Contexto anterior (opcional)
            on_tool_call: Callback para notificar tool calls
            max_iterations: Maximo de iteracoes

        Returns:
            (texto_final, contexto_atualizado)
        """
        system_prompt = self.build_system_prompt(task)

        if context:
            messages = list(context)
        else:
            messages = [{"role": "system", "content": system_prompt}]

        # Se nao havia contexto, a task ja esta no system prompt
        if not context:
            messages.append({"role": "user", "content": f"Executa a tarefa acima. Usa as ferramentas disponiveis para agir."})

        for iteration in range(max_iterations):
            try:
                response = await self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=2000,
                )
            except Exception as e:
                logger.error(f"[{self.agent_name}] Erro API: {e}")
                return f"Erro na API: {e}", messages

            msg = response.choices[0].message
            finish = response.choices[0].finish_reason
            messages.append(msg.model_dump(exclude_none=True))

            # Se o modelo parou ou nao quer usar tools
            if finish == "stop" or not msg.tool_calls:
                logger.info(f"[{self.agent_name}] Concluido em {iteration+1} iteracoes")
                return msg.content or "Tarefa concluida.", messages

            # Executar cada tool call
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                logger.info(f"[{self.agent_name}] Tool: {name}")

                # Notificar (ex: enviar para Telegram)
                if on_tool_call:
                    await on_tool_call(name, args, "")

                # Executar
                start_time = asyncio.get_event_loop().time()
                result = await execute_tool(name, args)
                elapsed = (asyncio.get_event_loop().time() - start_time) * 1000

                # Registar metrica
                success = "ERRO" not in str(result)[:10] and "erro" not in str(result)[:10].lower()
                self.metrics.track_tool_call(self.agent_name, name, elapsed, success)

                # Registar auditoria
                self.audit.log("tool_call", agent=self.agent_name, tool=name, args=args,
                              result=str(result)[:200], success=success, latency_ms=round(elapsed, 1))

                # Registar memoria episodica
                self.memory.record(name, args, str(result)[:200], success,
                                  context=f"Iteracao {iteration+1}")

                # Notificar resultado
                if on_tool_call:
                    await on_tool_call(name, args, str(result)[:500])

                # Adicionar resultado ao contexto
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)[:2000],
                })

        logger.warning(f"[{self.agent_name}] Limite de {max_iterations} iteracoes atingido")
        return "Limite de iteracoes atingido.", messages
