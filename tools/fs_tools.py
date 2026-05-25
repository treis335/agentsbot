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

logger = logging.getLogger(__name__)

# Configurações a partir do .env (com defaults para Windows)
REPO_DIR = Path(os.getenv("REPO_LOCAL_PATH", "C:/Users/Crypto Bull/Desktop/Agente Local"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "treis335/agentsbot")
AGENTS_FILE = Path("agents.json")

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
            "description": "Escreve conteúdo num ficheiro. Deves fornecer obrigatoriamente 'path' e 'content'.",
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
                    "code": {"type": "string"},
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
                    "name": {"type": "string"},
                    "mission": {"type": "string"},
                    "model": {"type": "string", "default": "deepseek-chat"}
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
                    "type": {"type": "string", "enum": ["code", "issues"]}
                },
                "required": ["query"]
            }
        }
    },
]

# ---------- Executor principal com logging e tolerância extrema ----------
async def execute_tool(name: str, args: dict) -> str:
    """Executa a ferramenta, aceitando múltiplos formatos de argumentos."""
    logger.info(f"Tool call: {name} with args: {args}")
    
    # Caso especial: argumentos vazios – retorna erro claro para o LLM corrigir
    if not args:
        return f"ERRO: A ferramenta '{name}' foi chamada sem argumentos. Para write_file, forneça 'path' e 'content'. Para read_file, forneça 'path'. Consulte a descrição da ferramenta."

    try:
        if name == "read_file":
            path = args.get("path") or args.get("file_path") or args.get("filename")
            if not path:
                return "ERRO: read_file precisa de 'path', 'file_path' ou 'filename'"
            return _read_file(path)

        elif name == "write_file":
            path = (args.get("path") or args.get("file_path") or 
                    args.get("filename") or args.get("file") or 
                    args.get("caminho"))
            content = (args.get("content") or args.get("data") or 
                       args.get("conteudo") or args.get("text") or
                       args.get("code"))
            if not path:
                return f"ERRO: write_file não encontrou 'path'. Argumentos recebidos: {list(args.keys())}"
            if content is None:
                return f"ERRO: write_file não encontrou 'content'. Argumentos recebidos: {list(args.keys())}"
            return _write_file(path, content)

        elif name == "list_files":
            subdir = args.get("subdir") or args.get("directory", "")
            return _list_files(subdir)

        elif name == "run_python":
            code = args.get("code") or args.get("python_code") or args.get("script")
            if not code:
                return "ERRO: run_python precisa de 'code'"
            timeout = args.get("timeout", 30)
            return await _run_python(code, timeout)

        elif name == "run_shell":
            command = args.get("command") or args.get("cmd") or args.get("shell")
            if not command:
                return "ERRO: run_shell precisa de 'command'"
            timeout = args.get("timeout", 60)
            return await _run_shell(command, timeout)

        elif name == "git_commit_push":
            message = args.get("message") or args.get("msg") or args.get("commit_message")
            if not message:
                message = "Update automático pelo agente"
            return await _git_commit_push(message)

        elif name == "git_status":
            return await _git_status()

        elif name == "create_agent":
            name_agent = args.get("name") or args.get("agent_name")
            mission = args.get("mission") or args.get("system_prompt") or args.get("description")
            if not name_agent or not mission:
                return "ERRO: create_agent precisa de 'name' e 'mission'"
            model = args.get("model", "deepseek-chat")
            return _create_agent(name_agent, mission, model)

        elif name == "search_github":
            query = args.get("query") or args.get("q")
            if not query:
                return "ERRO: search_github precisa de 'query'"
            search_type = args.get("type", "code")
            return _search_github(query, search_type)

        else:
            return f"Ferramenta desconhecida: {name}"

    except Exception as e:
        return f"ERRO em {name}: {traceback.format_exc()}"

# ---------- Implementações reais (adaptadas para Windows) ----------
def _ensure_repo():
    if not REPO_DIR.exists():
        REPO_DIR.mkdir(parents=True, exist_ok=True)
        if not GITHUB_TOKEN:
            url = f"https://github.com/{GITHUB_REPO}.git"
        else:
            url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        result = subprocess.run(
            ["git", "clone", url, str(REPO_DIR)],
            capture_output=True, text=True, timeout=120, shell=False
        )
        if result.returncode != 0:
            raise RuntimeError(f"Clone falhou: {result.stderr}")
        subprocess.run(["git", "config", "user.email", "correoto-bot@auto.ai"], cwd=REPO_DIR, shell=False)
        subprocess.run(["git", "config", "user.name", "Correoto Bot"], cwd=REPO_DIR, shell=False)
    else:
        try:
            subprocess.run(["git", "pull", "--rebase"], cwd=REPO_DIR, capture_output=True, timeout=30, shell=False)
        except Exception:
            pass

def _read_file(path: str) -> str:
    if not path:
        return "Caminho não fornecido"
    _ensure_repo()
    full = REPO_DIR / path
    if not full.exists():
        return f"Ficheiro não encontrado: {path}"
    content = full.read_text(encoding="utf-8", errors="replace")
    if len(content) > 8000:
        content = content[:8000] + "\n... [truncado]"
    return content

def _write_file(path: str, content: str) -> str:
    if not path:
        return "Caminho não fornecido"
    _ensure_repo()
    full = REPO_DIR / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return f"✅ Ficheiro escrito: {path} ({len(content)} chars)"

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
    if not code:
        return "Código vazio"
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
    if not command:
        return "Comando vazio"
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
        proc.kill()
        return f"Timeout após {timeout}s"

async def _git_commit_push(message: str) -> str:
    if not message:
        message = "Update automático pelo agente"
    _ensure_repo()
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
            output.append(f"⚠️ Returncode: {proc.returncode}")
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
    agents = []
    if AGENTS_FILE.exists():
        agents = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    new_agent = {
        "id": str(uuid.uuid4()),
        "name": name,
        "system_prompt": mission,
        "model": model,
        "status": "idle",
        "context": [],
        "metadata": {}
    }
    agents.append(new_agent)
    AGENTS_FILE.write_text(json.dumps(agents, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"✅ Agente '{name}' criado com ID {new_agent['id'][:8]}. agents.json atualizado."

def _search_github(query: str, search_type: str = "code") -> str:
    if not GITHUB_TOKEN:
        return "GitHub token não configurado."
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/search/{search_type}"
    params = {"q": f"{query} repo:{GITHUB_REPO}", "per_page": 5}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        items = data.get("items", [])
        if not items:
            return "Nenhum resultado encontrado."
        lines = []
        for item in items:
            lines.append(f"- {item.get('path', item.get('title', '?'))}: {item.get('html_url', '')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Erro na pesquisa GitHub: {e}"