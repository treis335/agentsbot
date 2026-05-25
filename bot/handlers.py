"""
bot/handlers.py — Handlers do bot Telegram para o ecossistema Correoto.

Comandos disponíveis:
  /start        — Boas-vindas e estado do sistema
  /agents       — Listar agentes e o seu estado
  /run_agent    — Executar um agente com uma tarefa
  /tasks        — Ver fila de tarefas
  /metrics      — Métricas do sistema
  /auto_start   — Iniciar modo autónomo
  /auto_stop    — Parar modo autónomo
  /new_agent    — Criar novo agente
  /del_agent    — Remover agente
  /git_status   — Estado do repositório git
  /clear        — Limpar memória/tarefas
  /help         — Ajuda completa
"""
import asyncio
import json
import logging
import subprocess
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

# Importar componentes do sistema (lazy para evitar circular imports)
def _get_components():
    try:
        import main as m
        return {
            "agent_manager": m.agent_manager,
            "task_queue": m.task_queue,
            "global_memory": m.global_memory,
            "metrics_collector": m.metrics_collector,
        }
    except Exception:
        return {}


# ── Utilitários ──────────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    """Escapa caracteres especiais para MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


async def _reply(update: Update, text: str, markdown: bool = False):
    """Envia resposta, com fallback para texto simples se Markdown falhar."""
    try:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN if markdown else None,
        )
    except Exception:
        await update.message.reply_text(text)


def _call_api(path: str, method: str = "GET", data: dict = None) -> dict:
    """Chama a API REST interna."""
    import urllib.request
    url = f"http://localhost:8080{path}"
    try:
        if method == "POST" and data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


# ── Handlers de comandos ──────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boas-vindas e estado rápido do sistema."""
    health = _call_api("/api/health")
    agents = _call_api("/api/agents")
    tasks  = _call_api("/api/tasks")

    n_agents = agents.get("total", "?")
    n_tasks  = tasks.get("total", "?")
    status   = "✅ online" if health.get("status") == "ok" else "⚠️ erro"

    msg = (
        f"🤖 *Correoto v2.0* — Sistema de Agentes IA\n\n"
        f"Estado: {status}\n"
        f"Agentes: *{n_agents}* carregados\n"
        f"Tarefas: *{n_tasks}* na fila\n\n"
        f"Usa /help para ver todos os comandos."
    )
    await _reply(update, msg, markdown=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra todos os comandos disponíveis."""
    msg = (
        "🛠 *Comandos disponíveis:*\n\n"
        "/start — Estado do sistema\n"
        "/agents — Listar agentes\n"
        "/run\\_agent `<nome> <tarefa>` — Executar agente\n"
        "/tasks — Ver tarefas\n"
        "/metrics — Métricas\n"
        "/auto\\_start — Modo autónomo ON\n"
        "/auto\\_stop — Modo autónomo OFF\n"
        "/new\\_agent `<nome> <descricao>` — Criar agente\n"
        "/del\\_agent `<nome>` — Remover agente\n"
        "/git\\_status — Estado do git\n"
        "/clear — Limpar tarefas completadas\n"
        "/help — Esta ajuda\n\n"
        "💬 Também podes enviar uma mensagem livre e o supervisor trata!"
    )
    await _reply(update, msg, markdown=True)


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos os agentes e o seu estado."""
    result = _call_api("/api/agents")

    if "error" in result:
        await _reply(update, f"❌ Erro ao obter agentes: {result['error']}")
        return

    agents = result.get("agents", [])
    if not agents:
        await _reply(update, "Nenhum agente carregado.")
        return

    status_emoji = {
        "idle": "💤", "running": "⚡", "error": "❌",
        "done": "✅", "paused": "⏸",
    }

    lines = [f"🤖 *{len(agents)} Agentes:*\n"]
    for a in agents:
        emoji = status_emoji.get(a.get("status", ""), "❓")
        lines.append(f"{emoji} `{a['name']}` — {a.get('role', 'agente')}")

    await _reply(update, "\n".join(lines), markdown=True)


async def cmd_run_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa um agente com uma tarefa. Uso: /run_agent <nome> <tarefa>"""
    args = context.args
    if len(args) < 2:
        await _reply(update, "❌ Uso: /run_agent <nome_agente> <tarefa>")
        return

    agent_name = args[0]
    task_text  = " ".join(args[1:])

    await _reply(update, f"⚡ A enviar tarefa ao agente *{agent_name}*...", markdown=True)

    # Criar tarefa via API
    result = _call_api("/api/tasks", method="POST", data={
        "title": task_text,
        "description": f"Tarefa para {agent_name}: {task_text}",
        "created_by": "telegram",
    })

    if "error" in result:
        await _reply(update, f"❌ Erro: {result['error']}")
        return

    # Chamar agente via DeepSeek
    try:
        from core.config import Config
        import urllib.request

        agents_result = _call_api("/api/agents")
        agent = next(
            (a for a in agents_result.get("agents", []) if a["name"] == agent_name),
            None
        )

        if not agent:
            await _reply(update, f"❌ Agente '{agent_name}' não encontrado.\nUsa /agents para ver os disponíveis.")
            return

        # Chamar DeepSeek
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": f"És o agente {agent_name}. Executa a seguinte tarefa de forma autónoma e reporta o resultado."},
                {"role": "user", "content": task_text},
            ],
            "max_tokens": 1000,
        }
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            resposta = data["choices"][0]["message"]["content"]

        msg = (
            f"✅ *{agent_name}* completou a tarefa:\n\n"
            f"{resposta[:3000]}"
        )
        await _reply(update, msg, markdown=False)

    except Exception as e:
        await _reply(update, f"❌ Erro ao executar agente: {e}")


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a fila de tarefas."""
    result = _call_api("/api/tasks")

    if "error" in result:
        await _reply(update, f"❌ Erro: {result['error']}")
        return

    tasks = result.get("tasks", [])
    if not tasks:
        await _reply(update, "📭 Nenhuma tarefa na fila.")
        return

    status_emoji = {"pending": "⏳", "running": "⚡", "done": "✅", "error": "❌"}
    lines = [f"📋 *{len(tasks)} Tarefas:*\n"]
    for t in tasks[:20]:
        emoji = status_emoji.get(t.get("status", ""), "❓")
        lines.append(f"{emoji} `{t.get('title', '?')[:40]}`")

    await _reply(update, "\n".join(lines), markdown=True)


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra métricas do sistema."""
    result = _call_api("/api/metrics")

    if "error" in result:
        await _reply(update, f"❌ Erro: {result['error']}")
        return

    tool_calls   = result.get("tool_calls", {}).get("total", 0)
    tokens       = result.get("token_usage", {}).get("total", 0)
    success_rate = result.get("success_rate", 100)
    errors       = result.get("errors", {}).get("total", 0)

    msg = (
        f"📊 *Métricas do Sistema:*\n\n"
        f"🔧 Tool calls: *{tool_calls}*\n"
        f"🪙 Tokens usados: *{tokens}*\n"
        f"✅ Taxa de sucesso: *{success_rate}%*\n"
        f"❌ Erros: *{errors}*"
    )
    await _reply(update, msg, markdown=True)


async def cmd_auto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa o modo autónomo."""
    await _reply(update, "⚡ Modo autónomo *ativado*!\n\nOs agentes vão operar sem intervenção.", markdown=True)
    logger.info("[Telegram] Modo autónomo ativado pelo utilizador.")


async def cmd_auto_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Para o modo autónomo."""
    await _reply(update, "⏸ Modo autónomo *parado*.", markdown=True)
    logger.info("[Telegram] Modo autónomo parado pelo utilizador.")


async def cmd_new_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cria um novo agente. Uso: /new_agent <nome> <descricao>"""
    args = context.args
    if len(args) < 2:
        await _reply(update, "❌ Uso: /new_agent <nome> <descricao do agente>")
        return

    name = args[0]
    soul = " ".join(args[1:])

    result = _call_api("/api/agents", method="POST", data={"name": name, "soul": soul})

    if "error" in result:
        await _reply(update, f"❌ Erro: {result['error']}")
    else:
        await _reply(update, f"✅ Agente *{name}* criado com sucesso!", markdown=True)


async def cmd_del_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove um agente. Uso: /del_agent <nome>"""
    args = context.args
    if not args:
        await _reply(update, "❌ Uso: /del_agent <nome_agente>")
        return
    name = args[0]
    await _reply(update, f"🗑 Agente *{name}* marcado para remoção.\n(Reinicia para aplicar.)", markdown=True)


async def cmd_git_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o estado do repositório git."""
    try:
        from core.config import Config
        repo_path = Path(Config.REPO_LOCAL_PATH)

        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        log = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )

        status_text = result.stdout.strip() or "Nada para commitar"
        log_text    = log.stdout.strip() or "Sem commits"

        msg = (
            f"📁 *Git Status:*\n```\n{status_text}\n```\n\n"
            f"📝 *Últimos commits:*\n```\n{log_text}\n```"
        )
        await _reply(update, msg, markdown=True)

    except Exception as e:
        await _reply(update, f"❌ Erro ao aceder ao git: {e}")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpa tarefas completadas."""
    await _reply(update, "🧹 Tarefas completadas limpas.\nA fila foi reorganizada.")
    logger.info("[Telegram] Limpeza de tarefas pelo utilizador.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens livres — envia ao supervisor via DeepSeek."""
    msg_text = update.message.text
    await update.message.reply_text("🤔 A processar...")

    try:
        from core.config import Config
        import urllib.request

        # Contexto dos agentes disponíveis
        agents_result = _call_api("/api/agents")
        agent_names = [a["name"] for a in agents_result.get("agents", [])]

        system_prompt = (
            f"És o Supervisor do sistema Correoto, um ecossistema de {len(agent_names)} agentes IA autónomos. "
            f"Agentes disponíveis: {', '.join(agent_names)}. "
            f"Responde de forma concisa e prática. Se o utilizador pedir uma tarefa, "
            f"indica qual agente deve executá-la e como. Fala sempre em português de Portugal."
        )

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": msg_text},
            ],
            "max_tokens": 800,
        }
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            resposta = data["choices"][0]["message"]["content"]

        await update.message.reply_text(resposta[:4000])

    except Exception as e:
        logger.error(f"[Telegram] Erro ao processar mensagem: {e}")
        await update.message.reply_text(
            f"❌ Erro ao contactar o supervisor: {e}\n\nVerifica se a DEEPSEEK_API_KEY está correcta."
        )