import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import traceback
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

# Carregar .env da raiz do projecto
_BASE = Path(__file__).parent.parent.resolve()
load_dotenv(_BASE / ".env")

logger = logging.getLogger(__name__)

# Força usar o caminho do config
try:
    from config import REPO_LOCAL_PATH
    REPO_DIR = Path(REPO_LOCAL_PATH)
except:
    _BASE = Path(__file__).parent.parent.resolve()
    REPO_DIR = Path(os.getenv("REPO_LOCAL_PATH", str(_BASE)))

print(f"[Tools] REPO_DIR: {REPO_DIR}")

REPO_DIR      = Path(os.getenv("REPO_LOCAL_PATH", str(_BASE)))
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO   = os.getenv("GITHUB_REPO", "treis335/agentsbot")
AGENTS_FILE   = _BASE / "agents" / "registry" / "agents.json"

# ---------- Definição das ferramentas (OpenAI function calling) ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lê o conteúdo de um ficheiro do repositório local.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Escreve conteúdo num ficheiro. Obrigatório: 'path' e 'content'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string"},
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
            "description": "Lista todos os ficheiros do repositório local.",
            "parameters": {
                "type": "object",
                "properties": {"subdir": {"type": "string"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Executa código Python e devolve stdout+stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code":    {"type": "string"},
                    "timeout": {"type": "integer"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Executa um comando shell no repositório local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit_push",
            "description": "Faz git add, commit e push para o GitHub.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Devolve o git status e git log dos últimos commits.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_agent",
            "description": "Cria um novo agente especialista no sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":    {"type": "string"},
                    "mission": {"type": "string"},
                    "model":   {"type": "string", "default": "deepseek-chat"}
                },
                "required": ["name", "mission"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_github",
            "description": "Pesquisa código ou issues no repositório via GitHub API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "type":  {"type": "string", "enum": ["code", "issues"]}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_website",
            "description": "Cria um site completo (HTML/CSS/JS) com múltiplas páginas. Usa para criar landing pages, portfolios, sites de produto, blogs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":        {"type": "string", "description": "Nome do site"},
                    "description": {"type": "string", "description": "O que o site faz / propósito"},
                    "pages":       {"type": "array", "items": {"type": "string"}, "description": "Páginas a criar, ex: ['index', 'sobre', 'contacto']"},
                    "style":       {"type": "string", "enum": ["modern", "minimal", "dark"], "description": "Estilo visual"},
                },
                "required": ["name", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_page",
            "description": "Adiciona uma nova página HTML a um site existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_name": {"type": "string", "description": "Nome do site"},
                    "page_name": {"type": "string", "description": "Nome da nova página"},
                    "content":   {"type": "string", "description": "HTML do conteúdo (opcional)"},
                },
                "required": ["site_name", "page_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_api",
            "description": "Chama a GitHub API directamente. Permite criar repos, activar Pages, criar issues, fazer qualquer operação GitHub. Usa quando precisas de criar repos, configurar settings, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method":   {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "description": "Método HTTP"},
                    "endpoint": {"type": "string", "description": "Endpoint GitHub API, ex: /user/repos ou /repos/owner/repo/pages"},
                    "body":     {"type": "object", "description": "Body JSON para POST/PATCH (opcional)"}
                },
                "required": ["method", "endpoint"]
            }
        }
    },
]

# ---------- Executor principal ----------
async def execute_tool(name: str, args: dict) -> str:
    """Executa a ferramenta, aceitando múltiplos formatos de argumentos."""
    logger.info(f"Tool call: {name} with args: {list(args.keys())}")

    if not args and name not in ("git_status", "list_files"):
        return (
            f"ERRO: A ferramenta '{name}' foi chamada sem argumentos. "
            "Consulta o schema no system prompt."
        )

    try:
        if name == "read_file":
            path = args.get("path") or args.get("file_path") or args.get("filename")
            if not path:
                return "ERRO: read_file precisa de 'path'"
            return _read_file(path)

        elif name == "write_file":
            path    = (args.get("path") or args.get("file_path") or
                       args.get("filename") or args.get("file") or args.get("caminho"))
            content = (args.get("content") or args.get("data") or
                       args.get("conteudo") or args.get("text") or args.get("code"))
            if not path:
                return f"ERRO: write_file não encontrou 'path'. Recebidos: {list(args.keys())}"
            if content is None:
                return f"ERRO: write_file não encontrou 'content'. Recebidos: {list(args.keys())}"
            return _write_file(path, content)

        elif name == "list_files":
            subdir = args.get("subdir") or args.get("directory", "")
            return _list_files(subdir)

        elif name == "run_python":
            code = args.get("code") or args.get("python_code") or args.get("script")
            if not code:
                return "ERRO: run_python precisa de 'code'"
            return await _run_python(code, args.get("timeout", 30))

        elif name == "run_shell":
            command = args.get("command") or args.get("cmd") or args.get("shell")
            if not command:
                return "ERRO: run_shell precisa de 'command'"
            return await _run_shell(command, args.get("timeout", 60))

        elif name == "git_commit_push":
            message = args.get("message") or args.get("msg") or args.get("commit_message")
            if not message:
                message = "Update automático pelo agente"
            return await _git_commit_push(message)

        elif name == "git_status":
            return await _git_status()

        elif name == "create_agent":
            name_agent = args.get("name") or args.get("agent_name")
            mission    = args.get("mission") or args.get("system_prompt") or args.get("description")
            if not name_agent or not mission:
                return "ERRO: create_agent precisa de 'name' e 'mission'"
            return _create_agent(name_agent, mission, args.get("model", "deepseek-chat"))

        elif name == "search_github":
            query = args.get("query") or args.get("q")
            if not query:
                return "ERRO: search_github precisa de 'query'"
            return _search_github(query, args.get("type", "code"))

        elif name == "github_api":
            return _github_api(
                method=args.get("method", "GET"),
                endpoint=args.get("endpoint", ""),
                body=args.get("body"),
            )

        elif name == "create_website":
            from tools.web_tools import create_website as _create_website
            return await _create_website(
                name=args.get("name", "meu-site"),
                description=args.get("description", ""),
                pages=args.get("pages", ["index"]),
                style=args.get("style", "modern"),
            )

        elif name == "add_page":
            from tools.web_tools import add_page as _add_page
            return await _add_page(
                site_name=args.get("site_name", ""),
                page_name=args.get("page_name", ""),
                content=args.get("content", ""),
            )

        else:
            return f"Ferramenta desconhecida: {name}"

    except Exception:
        return f"ERRO em {name}: {traceback.format_exc()}"


# ---------- Implementações reais ----------

def _ensure_repo():
    if not REPO_DIR.exists():
        REPO_DIR.mkdir(parents=True, exist_ok=True)
        url = (f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
               if GITHUB_TOKEN else f"https://github.com/{GITHUB_REPO}.git")
        result = subprocess.run(
            ["git", "clone", url, str(REPO_DIR)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f"Clone falhou: {result.stderr}")
        subprocess.run(["git", "config", "user.email", "correoto-bot@auto.ai"], cwd=REPO_DIR)
        subprocess.run(["git", "config", "user.name",  "Correoto Bot"],         cwd=REPO_DIR)
    else:
        try:
            subprocess.run(["git", "pull", "--rebase"], cwd=REPO_DIR,
                           capture_output=True, timeout=30)
        except Exception:
            pass


def _read_file(path: str) -> str:
    _ensure_repo()
    full = REPO_DIR / path
    if not full.exists():
        return f"Ficheiro não encontrado: {path}"
    content = full.read_text(encoding="utf-8", errors="replace")
    if len(content) > 8000:
        content = content[:8000] + "\n... [truncado]"
    return content


def _write_file(path: str, content: str) -> str:
    _ensure_repo()
    full = REPO_DIR / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    logger.info(f"[write_file] Escrito: {full}")
    return f"[OK] Ficheiro escrito: {path} ({len(content)} chars)"


def _list_files(subdir: str = "") -> str:
    _ensure_repo()
    base = REPO_DIR / subdir if subdir else REPO_DIR
    if not base.exists():
        return f"Diretório não encontrado: {subdir}"
    files = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts:
            files.append(str(p.relative_to(REPO_DIR)))
    return "\n".join(files) if files else "Nenhum ficheiro."


async def _run_python(code: str, timeout: int = 30) -> str:
    """Executa Python no servidor Linux. Usa sandbox Docker se SANDBOX_ENABLED=true e Docker disponível."""
    from core.config import Config
    if Config.SANDBOX_ENABLED:
        try:
            from sandbox.docker_runner import sandbox_runner
            if await sandbox_runner.is_available():
                result = await sandbox_runner.run_python(code=code, timeout=timeout)
                return result.to_tool_output()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[fs_tools] Sandbox falhou, execução directa: {e}")

    # Execução directa (sandbox desactivado ou Docker não disponível)
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        fname = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, fname,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_DIR)
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        result = ""
        if out:
            result += f"STDOUT:\n{out}"
        if err:
            result += f"STDERR:\n{err}"
        result += f"\nReturncode: {proc.returncode}"
        return result[:4000]
    except asyncio.TimeoutError:
        return f"Timeout após {timeout}s"
    finally:
        Path(fname).unlink(missing_ok=True)



async def _run_shell(command: str, timeout: int = 60) -> str:
    """Executa shell no servidor Linux. Usa sandbox Docker se SANDBOX_ENABLED=true e Docker disponível."""
    from core.config import Config
    if Config.SANDBOX_ENABLED:
        try:
            from sandbox.docker_runner import sandbox_runner
            if await sandbox_runner.is_available():
                result = await sandbox_runner.run_shell(command=command, timeout=timeout)
                return result.to_tool_output()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[fs_tools] Sandbox shell falhou, execução directa: {e}")

    # Execução directa (sandbox desactivado ou Docker não disponível)
    if not is_safe_command(command):
        return "[X] Comando bloqueado por razões de segurança."
    _ensure_repo()
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_DIR)
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        return (f"STDOUT:\n{out}\nSTDERR:\n{err}\nReturncode: {proc.returncode}")[:4000]
    except asyncio.TimeoutError:
        return f"Timeout após {timeout}s"



async def _git_commit_push(message: str) -> str:
    _ensure_repo()

    # ── Validar sintaxe Python antes de commitar ──────────────────────────
    import ast as _ast
    syntax_errors = []
    try:
        staged_proc = await asyncio.create_subprocess_exec(
            "git", "diff", "--cached", "--name-only",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_DIR)
        )
        staged_out, _ = await asyncio.wait_for(staged_proc.communicate(), timeout=10)
        staged_files = [f for f in staged_out.decode(errors="replace").strip().split("\n") if f.endswith(".py") and f.strip()]

        for rel_path in staged_files:
            full = REPO_DIR / rel_path
            if not full.exists():
                continue
            try:
                _ast.parse(full.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError as e:
                syntax_errors.append(f"{rel_path}: linha {e.lineno} — {e.msg}")
    except Exception:
        pass  # falha silenciosa — não bloquear por erro de verificação

    if syntax_errors:
        # Reverter git add e recusar commit
        await asyncio.create_subprocess_exec("git", "reset", "HEAD", cwd=str(REPO_DIR),
                                              stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        return (
            "[X] COMMIT BLOQUEADO — erros de sintaxe Python encontrados:\n" +
            "\n".join(syntax_errors) +
            "\n\nCorrige os erros e tenta de novo."
        )
    # ─────────────────────────────────────────────────────────────────────

    cmds = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", message],
        ["git", "push"],
    ]
    output = []
    for cmd in cmds:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_DIR)
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        output.append(f"$ {' '.join(cmd)}\n{out or err}")
        if proc.returncode != 0 and "nothing to commit" not in (out + err):
            output.append(f"[!]️ Returncode: {proc.returncode}")
            break
    return "\n".join(output)


async def _git_status() -> str:
    _ensure_repo()
    result = []
    for cmd in [["git", "status", "--short"], ["git", "log", "--oneline", "-10"]]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_DIR)
        )
        stdout, _ = await proc.communicate()
        result.append(stdout.decode(errors="replace").strip())
    return "\n---\n".join(result)


def _create_agent(name: str, mission: str, model: str = "deepseek-chat") -> str:
    if not name or not mission:
        return "ERRO: nome e missão são obrigatórios"
    AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    agents = []
    if AGENTS_FILE.exists():
        try:
            agents = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            agents = []
    new_agent = {
        "id":            str(uuid.uuid4()),
        "name":          name,
        "soul":          mission,
        "model":         model,
        "status":        "idle",
        "context":       [],
        "capabilities":  [],
        "metadata":      {},
        "created_at":    __import__("datetime").datetime.now().isoformat(),
        "last_active":   "",
        "role":          "custom",
    }
    agents.append(new_agent)
    AGENTS_FILE.write_text(json.dumps(agents, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"[OK] Agente '{name}' criado com ID {new_agent['id'][:8]}."

def is_safe_command(command: str) -> bool:
    """
    Bloqueia apenas comandos genuinamente destrutivos.
    Git, ls, cat, python3, pip — tudo permitido.
    """
    cmd_lower = command.lower().strip()
    BLOCKED = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=/dev/zero",
        ":(){ :|:& };:",
        "> /dev/sda",
        "shutdown -",
        "reboot",
        "halt",
        "kill -9 1",
        "cat .env | curl",
        "cat .env | nc",
    ]
    return not any(bad in cmd_lower for bad in BLOCKED)




def _github_api(method: str, endpoint: str, body: dict = None) -> str:
    """
    Chama a GitHub API directamente.
    Permite criar repos, activar Pages, criar issues, etc.
    """
    if not GITHUB_TOKEN:
        return "[X] GITHUB_TOKEN não configurado no .env"
    if not endpoint:
        return "[X] endpoint obrigatório (ex: /user/repos)"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    url = f"https://api.github.com{endpoint}"

    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=body,
            timeout=15,
        )
        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code in (200, 201, 204):
            # Sucesso — retornar info útil
            if isinstance(data, dict):
                useful = {k: data[k] for k in ("html_url", "full_name", "name", "message", "url") if k in data}
                return f"[OK] {method} {endpoint} → {resp.status_code}\n{useful or data}"
            return f"[OK] {method} {endpoint} → {resp.status_code}\n{str(data)[:500]}"
        else:
            msg = data.get("message", str(data)) if isinstance(data, dict) else str(data)
            return f"[X] GitHub API {resp.status_code}: {msg}"
    except Exception as e:
        return f"[X] Erro ao chamar GitHub API: {e}"


def _search_github(query: str, search_type: str = "code") -> str:
    if not GITHUB_TOKEN:
        return "GitHub token não configurado."
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    url     = f"https://api.github.com/search/{search_type}"
    params  = {"q": f"{query} repo:{GITHUB_REPO}", "per_page": 5}
    try:
        r    = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        items = data.get("items", [])
        if not items:
            return "Nenhum resultado encontrado."
        return "\n".join(
            f"- {item.get('path', item.get('title', '?'))}: {item.get('html_url', '')}"
            for item in items
        )
    except Exception as e:
        return f"Erro na pesquisa GitHub: {e}"