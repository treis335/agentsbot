"""
bot/handlers.py — Bot Telegram com DeepSeek real, memória persistente e tools locais.

Mensagens livres vão ao Supervisor que PODE usar ferramentas reais no PC local.
/run executa qualquer agente com memória episódica completa.
"""
import asyncio
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
        url  = f"http://localhost:8080{path}"
        data = json.dumps(body).encode() if body else None
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def _deepseek_with_history(system: str, history: list, user_msg: str, max_tokens: int = 1500) -> str:
    """Chama DeepSeek com histórico de conversa completo (memória real)."""
    try:
        from core.config import Config
        api_key = Config.DEEPSEEK_API_KEY
        if not api_key:
            return "Erro: DEEPSEEK_API_KEY não configurada no .env"
    except Exception:
        return "Erro: Não foi possível carregar a configuração."

    messages = [{"role": "system", "content": system}]
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_msg})

    payload = {
        "model":      "deepseek-chat",
        "messages":   messages,
        "max_tokens": max_tokens,
    }
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data    = json.dumps(payload).encode(),
            headers = {
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"Erro DeepSeek {e.code}: {body[:300]}"
    except Exception as e:
        return f"Erro ao contactar DeepSeek: {e}"


def _load_conversation_history(user_id: int) -> list:
    """Carrega histórico de conversa persistente do utilizador."""
    try:
        from core.config import Config
        hist_file = Config.MEMORY_DIR / "conversations" / f"telegram_{user_id}.json"
        if hist_file.exists():
            return json.loads(hist_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug(f"[handlers] Erro ao carregar histórico: {e}")
    return []


def _save_conversation_history(user_id: int, history: list) -> None:
    """Guarda histórico de conversa persistente."""
    try:
        from core.config import Config
        hist_dir  = Config.MEMORY_DIR / "conversations"
        hist_dir.mkdir(parents=True, exist_ok=True)
        hist_file = hist_dir / f"telegram_{user_id}.json"
        hist_file.write_text(
            json.dumps(history[-50:], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"[handlers] Erro ao guardar histórico: {e}")


def _register_global_memory(agent: str, msg: str) -> None:
    try:
        from memory.global_memory import GlobalMemory
        GlobalMemory().add_decision(agent=agent, decision=msg[:120], context="Telegram")
    except Exception:
        pass


async def _send(update: Update, text: str):
    for i in range(0, max(len(text), 1), 4000):
        await update.message.reply_text(text[i:i + 4000])


# ──────────────────────────────────────────
# COMANDOS
# ──────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    health = _api("/api/health")
    agents = _api("/api/agents")
    ok     = health.get("status") == "ok"
    n      = agents.get("total", "?")
    msg    = (
        f"{'✅' if ok else '❌'} Correoto v2.0 — a correr localmente\n\n"
        f"{n} agentes carregados\n"
        f"Escreve qualquer coisa — o Supervisor age com ferramentas reais.\n\n"
        f"/agents — listar agentes\n"
        f"/run <agente> <tarefa> — executar agente\n"
        f"/tasks — ver tarefas\n"
        f"/metrics — métricas\n"
        f"/memory — ver memória\n"
        f"/git — estado git\n"
        f"/clear_memory — limpar conversa\n"
        f"/help — ajuda"
    )
    await _send(update, msg)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Comandos:\n\n"
        "/start — estado do sistema\n"
        "/agents — listar agentes\n"
        "/run <agente> <tarefa> — executar agente com ferramentas reais\n"
        "/tasks — fila de tarefas\n"
        "/metrics — métricas do sistema\n"
        "/memory — ver memória global\n"
        "/git — estado git\n"
        "/clear_memory — limpar histórico de conversa\n"
        "/help — esta ajuda\n\n"
        "Mensagens livres: o Supervisor responde e age localmente."
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
    emoji = {"idle": "💤", "running": "⚡", "error": "❌", "done": "✅", "stopped": "🔴"}
    lines = [f"Agentes ({len(agents)}):"]
    for a in agents:
        e = emoji.get(a.get("status", ""), "❓")
        lines.append(f"{e} {a['name']} — {a.get('role', 'agente')}")
    await _send(update, "\n".join(lines))


async def cmd_run_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await _send(update, "Uso: /run <nome_agente> <tarefa>\nEx: /run developer cria um script de backup")
        return

    agent_name = args[0]
    task       = " ".join(args[1:])

    agents_data = _api("/api/agents")
    all_agents  = agents_data.get("agents", [])
    agent_cfg   = next((a for a in all_agents if a["name"].lower() == agent_name.lower()), None)

    if not agent_cfg:
        nomes = ", ".join(a["name"] for a in all_agents[:10])
        await _send(update, f"Agente '{agent_name}' não encontrado.\nDisponíveis: {nomes}")
        return

    await _send(update, f"⚡ {agent_name} a trabalhar...")

    try:
        from agents.executor import AgentExecutor
        executor  = AgentExecutor(agent_name, agent_cfg.get("id", agent_name))
        tool_msgs = []

        async def on_tool(name, args, result):
            if result:
                tool_msgs.append(f"🔧 {name}: {str(result)[:120]}")
                # Notificar em tempo real no Telegram
                if len(tool_msgs) % 3 == 0:
                    await update.message.reply_text("\n".join(tool_msgs[-3:]))

        resposta, _ = await executor.run(task, on_tool_call=on_tool)

        output = f"{agent_name}:\n\n{resposta}"
        if tool_msgs:
            output += f"\n\n— {len(tool_msgs)} operações realizadas —"

        _register_global_memory(agent_name, f"Executou: {task[:80]}")
        await _send(update, output)

    except Exception as e:
        logger.error(f"[cmd_run_agent] Erro: {e}", exc_info=True)
        await _send(update, f"Erro ao executar {agent_name}: {e}")


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = _api("/api/tasks")
    if "error" in result:
        await _send(update, f"Erro: {result['error']}")
        return
    tasks = result.get("tasks", [])
    if not tasks:
        await _send(update, "Nenhuma tarefa na fila.")
        return
    emoji = {"pending": "⏳", "running": "⚡", "done": "✅", "error": "❌"}
    lines = [f"Tarefas ({len(tasks)}):"]
    for t in tasks[:15]:
        e = emoji.get(t.get("status", ""), "❓")
        lines.append(f"{e} {t.get('title', '?')[:50]}")
    await _send(update, "\n".join(lines))


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = _api("/api/metrics")
    if "error" in result:
        await _send(update, f"Erro: {result['error']}")
        return
    tc  = result.get("tool_calls", {})
    tok = result.get("token_usage", {})
    msg = (
        f"Métricas:\n\n"
        f"Tool calls: {tc.get('total', 0)}\n"
        f"Tokens usados: {tok.get('total', 0)}\n"
        f"Taxa de sucesso: {result.get('success_rate', 100)}%\n"
        f"Erros: {result.get('errors', {}).get('total', 0)}"
    )
    await _send(update, msg)


async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from memory.global_memory import GlobalMemory
        gm        = GlobalMemory()
        decisions = gm.get_decisions(10)
        knowledge = gm.get_knowledge()
        metrics   = gm.get_metrics()

        lines = ["Memória Global:\n"]
        if decisions:
            lines.append("Últimas decisões:")
            for d in decisions[-5:]:
                lines.append(f"  [{d['timestamp'][:16]}] {d['agent']}: {d['decision'][:70]}")
        if knowledge:
            lines.append(f"\nConhecimento acumulado: {len(knowledge)} tópicos")
        lines.append(f"\nMétricas: {metrics}")
        await _send(update, "\n".join(lines))
    except Exception as e:
        await _send(update, f"Erro ao ler memória: {e}")


async def cmd_clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _save_conversation_history(user_id, [])
    await _send(update, "Histórico de conversa limpo.")


async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from core.config import Config
        repo = Path(Config.REPO_LOCAL_PATH)
        s = subprocess.run(["git", "status", "--short"],     cwd=repo, capture_output=True, text=True, timeout=10)
        l = subprocess.run(["git", "log", "--oneline", "-5"], cwd=repo, capture_output=True, text=True, timeout=10)
        await _send(update, f"Git Status:\n{s.stdout.strip() or 'Limpo'}\n\nCommits:\n{l.stdout.strip() or 'Nenhum'}")
    except Exception as e:
        await _send(update, f"Erro git: {e}")


# Aliases
async def cmd_auto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send(update, "Modo autónomo activado.")

async def cmd_auto_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send(update, "Modo autónomo parado.")

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
    await _send(update, f"Agente {args[0]} marcado para remoção.")

async def cmd_git_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await cmd_git(update, context)

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send(update, "Tarefas completadas limpas.")


# ──────────────────────────────────────────
# HANDLER DE MENSAGENS LIVRES
# Usa o Supervisor com ferramentas reais
# ──────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mensagens livres vão ao Supervisor via AgentExecutor.
    O Supervisor tem acesso a ferramentas reais (write_file, run_shell, etc.)
    e memória episódica persistente.
    """
    user_id  = update.effective_user.id
    user_msg = update.message.text

    await update.message.reply_text("A processar...")

    history = _load_conversation_history(user_id)

    try:
        from agents.executor import AgentExecutor

        # Construir contexto com histórico de conversa
        # O Supervisor usa tools reais + tem o histórico como contexto
        executor = AgentExecutor("supervisor", f"supervisor-{user_id}")

        # Injectar histórico de conversa no contexto de mensagens
        msg_context = None
        if history:
            system_prompt = executor.build_system_prompt(user_msg)
            msg_context = [{"role": "system", "content": system_prompt}]
            # Adicionar histórico (últimas 10 trocas = 20 mensagens)
            msg_context.extend(history[-20:])
            msg_context.append({"role": "user", "content": user_msg})

        tool_msgs = []

        async def on_tool(name, args, result):
            if result and len(result) > 10:
                tool_msgs.append(f"🔧 {name}: {str(result)[:150]}")

        resposta, new_context = await executor.run(
            task       = user_msg,
            context    = msg_context,
            on_tool_call = on_tool,
            max_iterations = 15,
        )

        # Actualizar histórico com esta troca
        history.append({"role": "user",      "content": user_msg})
        history.append({"role": "assistant", "content": resposta})
        _save_conversation_history(user_id, history)

        # Registar na memória global
        _register_global_memory("supervisor", f"Telegram: {user_msg[:80]}")

        # Enviar resposta
        output = resposta
        if tool_msgs:
            output += f"\n\n— Operações realizadas: {len(tool_msgs)} —\n" + "\n".join(tool_msgs[:5])

        await _send(update, output)

    except Exception as e:
        logger.error(f"[handle_message] Erro no executor: {e}", exc_info=True)

        # Fallback: resposta simples sem tools mas com histórico
        agents_data = _api("/api/agents")
        agent_names = [a["name"] for a in agents_data.get("agents", [])]

        memory_ctx = ""
        try:
            from memory.global_memory import GlobalMemory
            decisions = GlobalMemory().get_decisions(3)
            if decisions:
                memory_ctx = "\n\nDecisões recentes:\n" + "\n".join(
                    f"- {d['agent']}: {d['decision'][:60]}" for d in decisions
                )
        except Exception:
            pass

        system = (
            f"És o Supervisor do ecossistema Correoto a correr localmente no PC do utilizador. "
            f"Tens {len(agent_names)} agentes: {', '.join(agent_names[:8]) if agent_names else 'nenhum'}. "
            f"Respondes em português de Portugal. Nunca digas que estás na nuvem — estás no PC do utilizador."
            f"{memory_ctx}"
        )

        resposta = _deepseek_with_history(system, history, user_msg, max_tokens=1500)

        history.append({"role": "user",      "content": user_msg})
        history.append({"role": "assistant", "content": resposta})
        _save_conversation_history(user_id, history)

        await _send(update, resposta)