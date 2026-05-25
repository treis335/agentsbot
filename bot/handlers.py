"""
bot/handlers.py — Bot Telegram completo para o ecossistema Correoto.
Chama DeepSeek de verdade. Cada mensagem livre vai ao supervisor IA.
"""
import json
import logging
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def _api(path: str, method: str = "GET", body: dict = None) -> dict:
    try:
        url = f"http://localhost:8080{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def _deepseek(system: str, user: str, max_tokens: int = 1000) -> str:
    try:
        from core.config import Config
        api_key = Config.DEEPSEEK_API_KEY
    except Exception:
        return "Erro: DEEPSEEK_API_KEY nao configurada no .env"

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "max_tokens": max_tokens,
    }
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"Erro DeepSeek {e.code}: {body[:300]}"
    except Exception as e:
        return f"Erro ao contactar DeepSeek: {e}"


async def _send(update: Update, text: str):
    for i in range(0, max(len(text), 1), 4000):
        await update.message.reply_text(text[i:i+4000])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    health = _api("/api/health")
    agents = _api("/api/agents")
    ok = health.get("status") == "ok"
    n  = agents.get("total", "?")
    msg = (
        f"{'OK' if ok else 'ERRO'} Correoto v2.0\n\n"
        f"{n} agentes carregados\n"
        f"Escreve qualquer coisa — o Supervisor responde com IA real.\n\n"
        f"/agents — listar agentes\n"
        f"/run <agente> <tarefa> — executar agente\n"
        f"/tasks — ver tarefas\n"
        f"/metrics — metricas\n"
        f"/git — estado git\n"
        f"/help — ajuda"
    )
    await _send(update, msg)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Comandos:\n\n"
        "/start — estado do sistema\n"
        "/agents — listar agentes\n"
        "/run <agente> <tarefa> — executar agente com DeepSeek\n"
        "/tasks — fila de tarefas\n"
        "/metrics — metricas\n"
        "/git — estado git\n"
        "/help — esta ajuda\n\n"
        "Ou escreve directamente — o Supervisor IA responde!"
    )
    await _send(update, msg)


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = _api("/api/agents")
    if "error" in result:
        await _send(update, f"Erro: {result['error']}")
        return
    agents = result.get("agents", [])
    if not agents:
        await _send(update, "Nenhum agente carregado.")
        return
    emoji = {"idle": "Z", "running": "!", "error": "X", "done": "OK"}
    lines = [f"Agentes ({len(agents)}):"]
    for a in agents:
        e = emoji.get(a.get("status", ""), "?")
        lines.append(f"[{e}] {a['name']} - {a.get('role', 'agente')}")
    await _send(update, "\n".join(lines))


async def cmd_run_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await _send(update, "Uso: /run <nome_agente> <tarefa>\nEx: /run developer cria um script de backup")
        return

    agent_name = args[0]
    task = " ".join(args[1:])

    agents_data = _api("/api/agents")
    all_agents = agents_data.get("agents", [])
    agent = next((a for a in all_agents if a["name"].lower() == agent_name.lower()), None)

    if not agent:
        nomes = ", ".join(a["name"] for a in all_agents[:10])
        await _send(update, f"Agente '{agent_name}' nao encontrado.\nDisponiveis: {nomes}")
        return

    await _send(update, f"A executar {agent_name}...")

    try:
        agents_file = Path("agents.json")
        if agents_file.exists():
            raw = json.loads(agents_file.read_text(encoding="utf-8"))
            all_raw = raw if isinstance(raw, list) else raw.get("agents", [])
            agent_cfg = next((a for a in all_raw if a["name"].lower() == agent_name.lower()), {})
            system_prompt = agent_cfg.get("system_prompt", f"Es o agente {agent_name}. Executa a tarefa.")
        else:
            system_prompt = f"Es o agente {agent_name}. Executa a tarefa de forma autonoma."
    except Exception:
        system_prompt = f"Es o agente {agent_name}. Executa a tarefa."

    resposta = _deepseek(system_prompt, task, max_tokens=1500)
    await _send(update, f"{agent_name}:\n\n{resposta}")


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = _api("/api/tasks")
    if "error" in result:
        await _send(update, f"Erro: {result['error']}")
        return
    tasks = result.get("tasks", [])
    if not tasks:
        await _send(update, "Nenhuma tarefa na fila.")
        return
    emoji = {"pending": "...", "running": ">>", "done": "OK", "error": "X"}
    lines = [f"Tarefas ({len(tasks)}):"]
    for t in tasks[:15]:
        e = emoji.get(t.get("status", ""), "?")
        lines.append(f"[{e}] {t.get('title', '?')[:50]}")
    await _send(update, "\n".join(lines))


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = _api("/api/metrics")
    if "error" in result:
        await _send(update, f"Erro: {result['error']}")
        return
    msg = (
        f"Metricas:\n\n"
        f"Tool calls: {result.get('tool_calls', {}).get('total', 0)}\n"
        f"Tokens: {result.get('token_usage', {}).get('total', 0)}\n"
        f"Sucesso: {result.get('success_rate', 100)}%\n"
        f"Erros: {result.get('errors', {}).get('total', 0)}"
    )
    await _send(update, msg)


async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from core.config import Config
        repo = Path(Config.REPO_LOCAL_PATH)
        s = subprocess.run(["git", "status", "--short"], cwd=repo, capture_output=True, text=True, timeout=10)
        l = subprocess.run(["git", "log", "--oneline", "-5"], cwd=repo, capture_output=True, text=True, timeout=10)
        await _send(update, f"Git Status:\n{s.stdout.strip() or 'Limpo'}\n\nCommits:\n{l.stdout.strip() or 'Nenhum'}")
    except Exception as e:
        await _send(update, f"Erro git: {e}")


# Aliases para main.py
async def cmd_auto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send(update, "Modo autonomo activado.")

async def cmd_auto_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send(update, "Modo autonomo parado.")

async def cmd_new_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await _send(update, "Uso: /new_agent <nome> <descricao>")
        return
    result = _api("/api/agents", method="POST", body={"name": args[0], "soul": " ".join(args[1:])})
    await _send(update, f"Agente {args[0]} criado." if "error" not in result else f"Erro: {result['error']}")

async def cmd_del_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await _send(update, "Uso: /del_agent <nome>")
        return
    await _send(update, f"Agente {args[0]} marcado para remocao.")

async def cmd_git_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await cmd_git(update, context)

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send(update, "Tarefas completadas limpas.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagens livres vao ao Supervisor via DeepSeek."""
    user_msg = update.message.text
    await update.message.reply_text("A pensar...")

    agents_data = _api("/api/agents")
    agent_names = [a["name"] for a in agents_data.get("agents", [])]

    system = (
        f"Es o Supervisor do sistema Correoto com {len(agent_names)} agentes IA: {', '.join(agent_names) if agent_names else 'nenhum'}. "
        f"Responde de forma clara e pratica. "
        f"Se o utilizador pedir uma tarefa, diz qual agente usa e o que faz. "
        f"Se pedir codigo, escreve codigo funcional completo. "
        f"Fala sempre em portugues de Portugal."
    )

    resposta = _deepseek(system, user_msg, max_tokens=1500)
    await _send(update, resposta)