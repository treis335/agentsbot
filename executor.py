"""
executor.py — Executor robusto de tarefas de agentes.

Melhorias:
  - Validação e normalização de argumentos ANTES de chamar o LLM em loop
  - Retry inteligente com feedback estruturado ao modelo
  - Sem loops infinitos de "run_python sem argumentos"
  - Tool call schema injectado no system prompt para o modelo nunca esquecer
"""
import json
import logging
from typing import Callable, Awaitable

from openai import AsyncOpenAI
from tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MAX_ITERATIONS = 30
MAX_RETRIES_PER_TOOL = 2

# Esquema resumido das ferramentas — é injectado no início de cada conversa
# para que o modelo nunca esqueça os argumentos obrigatórios.
TOOL_SCHEMA_REMINDER = """
## FERRAMENTAS DISPONÍVEIS — ARGUMENTOS OBRIGATÓRIOS

| Ferramenta       | Argumentos obrigatórios                          | Exemplo                                              |
|------------------|--------------------------------------------------|------------------------------------------------------|
| write_file       | path (str), content (str)                        | write_file(path="src/main.py", content="print(1)")   |
| read_file        | path (str)                                       | read_file(path="src/main.py")                        |
| run_python       | code (str)                                       | run_python(code="print('olá')")                      |
| run_shell        | command (str)                                    | run_shell(command="ls -la")                          |
| create_agent     | name (str), mission (str)                        | create_agent(name="Tester", mission="Faz testes")    |
| web_search       | query (str)                                      | web_search(query="python asyncio tutorial")          |
| git_commit_push  | message (str)                                    | git_commit_push(message="feat: add feature")         |
| list_files       | path (str, opcional, default=".")                | list_files(path="src/")                              |

REGRA DE OURO: Nunca chames uma ferramenta sem os argumentos obrigatórios.
Se não tens o valor de um argumento, descobre-o primeiro (ex: usa list_files ou read_file).
"""


# ---------------------------------------------------------------------------
# Validação e normalização de argumentos
# ---------------------------------------------------------------------------

# Aliases comuns que o modelo usa em vez dos nomes canónicos
_FIELD_ALIASES = {
    "write_file": {
        "path":    ["file_path", "filename", "file", "filepath", "name"],
        "content": ["data", "text", "body", "source", "code", "contents"],
    },
    "read_file": {
        "path": ["file_path", "filename", "file", "filepath"],
    },
    "run_python": {
        "code": ["script", "python_code", "source", "program"],
    },
    "run_shell": {
        "command": ["cmd", "shell", "bash", "shell_command"],
    },
    "create_agent": {
        "name":    ["agent_name", "agente"],
        "mission": ["task", "description", "role", "objetivo", "missao"],
    },
    "web_search": {
        "query": ["q", "search", "term", "keywords"],
    },
    "git_commit_push": {
        "message": ["msg", "commit_message", "commit_msg"],
    },
}

_REQUIRED_FIELDS = {
    "write_file":      ["path", "content"],
    "read_file":       ["path"],
    "run_python":      ["code"],
    "run_shell":       ["command"],
    "create_agent":    ["name", "mission"],
    "web_search":      ["query"],
    "git_commit_push": ["message"],
}


def _normalize_args(tool_name: str, args: dict) -> dict:
    """Resolve aliases para os nomes canónicos dos argumentos."""
    aliases = _FIELD_ALIASES.get(tool_name, {})
    normalized = dict(args)
    for canonical, alts in aliases.items():
        if canonical not in normalized:
            for alt in alts:
                if alt in args:
                    normalized[canonical] = args[alt]
                    break
    return normalized


def _validate_args(tool_name: str, args: dict) -> tuple[bool, str | None]:
    """Valida se os argumentos obrigatórios estão presentes e não são vazios."""
    required = _REQUIRED_FIELDS.get(tool_name)
    if required is None:
        return True, None  # ferramenta desconhecida, deixa passar

    missing = [f for f in required if not args.get(f)]
    if missing:
        examples = {
            "write_file":      'write_file(path="ficheiro.py", content="# código aqui")',
            "read_file":       'read_file(path="ficheiro.py")',
            "run_python":      'run_python(code="print(\'olá\')")',
            "run_shell":       'run_shell(command="ls -la")',
            "create_agent":    'create_agent(name="Nome", mission="Missão detalhada")',
            "web_search":      'web_search(query="o que pesquisar")',
            "git_commit_push": 'git_commit_push(message="feat: descrição")',
        }
        ex = examples.get(tool_name, f"{tool_name}({', '.join(f'{f}=...' for f in required)})")
        msg = (
            f"❌ {tool_name}: campos obrigatórios em falta: {missing}.\n"
            f"   Recebido: {json.dumps(args, ensure_ascii=False)}\n"
            f"   Exemplo correcto: {ex}\n"
            f"   Corrige a chamada e tenta novamente com os argumentos correctos."
        )
        return False, msg
    return True, None


# ---------------------------------------------------------------------------
# Executor principal
# ---------------------------------------------------------------------------

async def run_agent_task(
    system_prompt: str,
    task: str,
    api_key: str,
    model: str = "deepseek-chat",
    on_tool_call: Callable[[str, dict, str], Awaitable[None]] | None = None,
    context: list | None = None,
) -> tuple[str, list]:
    client = AsyncOpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    # Injeta o schema das ferramentas no system prompt para reduzir erros
    enriched_system = system_prompt.rstrip() + "\n\n" + TOOL_SCHEMA_REMINDER

    if context:
        messages = list(context)
    else:
        messages = [{"role": "system", "content": enriched_system}]

    messages.append({"role": "user", "content": task})

    for iteration in range(MAX_ITERATIONS):
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=2000,
        )
        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        messages.append(msg.model_dump(exclude_none=True))

        if finish_reason == "stop" or not msg.tool_calls:
            final_text = msg.content or "✅ Tarefa concluída."
            logger.info(f"[Executor] Concluída em {iteration + 1} iteração(ões).")
            return final_text, messages

        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            raw_args = tool_call.function.arguments

            # Parse dos argumentos
            try:
                func_args = json.loads(raw_args) if raw_args else {}
                if not isinstance(func_args, dict):
                    func_args = {}
            except json.JSONDecodeError:
                func_args = {}

            # Normaliza aliases
            func_args = _normalize_args(func_name, func_args)

            # Valida argumentos obrigatórios
            is_valid, error_msg = _validate_args(func_name, func_args)

            # Loop de retry com feedback ao modelo
            for retry in range(MAX_RETRIES_PER_TOOL):
                if is_valid:
                    break

                logger.warning(
                    f"[Executor] Tool inválida '{func_name}' (tentativa {retry+1}): {func_args}"
                )
                if on_tool_call:
                    await on_tool_call(func_name, func_args, error_msg)

                # Regista o erro no histórico e pede correcção
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": error_msg,
                })
                correction_resp = await client.chat.completions.create(
                    model=model,
                    messages=messages + [{
                        "role": "user",
                        "content": (
                            f"A chamada a '{func_name}' falhou por falta de argumentos. "
                            f"Repete a chamada AGORA com os argumentos correctos e completos. "
                            f"Consulta o esquema no teu system prompt."
                        ),
                    }],
                    tools=TOOLS,
                    tool_choice={"type": "function", "function": {"name": func_name}},
                    temperature=0.1,
                    max_tokens=600,
                )
                corr_msg = correction_resp.choices[0].message
                if corr_msg.tool_calls:
                    new_tc = corr_msg.tool_calls[0]
                    try:
                        new_args = json.loads(new_tc.function.arguments)
                    except Exception:
                        new_args = {}
                    new_args = _normalize_args(func_name, new_args)
                    is_valid, error_msg = _validate_args(func_name, new_args)
                    if is_valid:
                        func_args = new_args
                        # substitui o tool_call_id corrente pelo novo
                        tool_call = new_tc
                else:
                    # modelo não devolveu tool_call, falha definitiva
                    break

            if not is_valid:
                final_error = (
                    f"❌ '{func_name}' falhou após {MAX_RETRIES_PER_TOOL} tentativas. "
                    f"Argumentos inválidos: {json.dumps(func_args, ensure_ascii=False)}"
                )
                logger.error(f"[Executor] {final_error}")
                if on_tool_call:
                    await on_tool_call(func_name, func_args, final_error)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": final_error,
                })
                continue

            # Executa a tool com argumentos válidos
            logger.info(f"[Executor] {func_name}({list(func_args.keys())})")
            result = await execute_tool(func_name, func_args)

            if on_tool_call:
                await on_tool_call(func_name, func_args, result)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

    return "⚠️ Limite de iterações atingido.", messages