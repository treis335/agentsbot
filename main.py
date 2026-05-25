import asyncio
import json
import logging
from pathlib import Path

import aiofiles
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)

from config import (
    TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
    LOG_LEVEL, MASTER_MEMORY_FILE, MEMORY_DIR, AGENT_INTERVAL,
)
from manager import AgentManager
from executor import run_agent_task
from tools import TOOLS, execute_tool
from tools.fs_tools import _git_status

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
manager = AgentManager(api_key=DEEPSEEK_API_KEY, interval=AGENT_INTERVAL)

MASTER_SYSTEM = """És o Arquiteto Mestre de um ecossistema autónomo de agentes IA.
Tens acesso a ferramentas reais: lês e escreves ficheiros, execitas Python, fazes git commits, crias agentes novos, pesquisas na web.
 
Quando o utilizador te pede algo, usa as ferramentas disponíveis para FAZER mesmo — não apenas descrever.
 
## REGRAS ABSOLUTAS PARA FERRAMENTAS
 
Nunca chames uma ferramenta sem fornecer TODOS os argumentos obrigatórios.
Se o valor de um argumento não está disponível, usa outra ferramenta para obtê-lo primeiro.
 
| Ferramenta       | Argumentos OBRIGATÓRIOS       | Exemplo correcto                                           |
|------------------|-------------------------------|------------------------------------------------------------|
| write_file       | path, content                 | write_file(path="src/bot.py", content="# código")         |
| read_file        | path                          | read_file(path="src/bot.py")                              |
| run_python       | code                          | run_python(code="import os; print(os.listdir('.'))")      |
| run_shell        | command                       | run_shell(command="git status")                           |
| create_agent     | name, mission                 | create_agent(name="Monitor", mission="Monitoriza o sistema") |
| web_search       | query                         | web_search(query="python asyncio best practices 2025")    |
| git_commit_push  | message                       | git_commit_push(message="fix: corrige validação de args") |
 
## FLUXO CORRECTO
 
Antes de escrever um ficheiro: se não sabes o conteúdo completo, usa read_file primeiro.
Antes de executar Python: o argumento "code" deve ser uma string com código Python válido.
Nunca chames a mesma ferramenta com argumentos vazios — se tens dúvida sobre um valor, pesquisa ou lê primeiro.
 
## CAPACIDADES
 
- Criar, ler, editar ficheiros do projecto
- Executar Python e shell
- Fazer git commit e push automático
- Criar e gerir agentes autónomos
- Pesquisar na internet informação actualizada
- Diagnosticar e corrigir bugs no código
 
Reporta sempre o que fizeste com os resultados reais das ferramentas.
"""

master_context: list = [{"role": "system", "content": MASTER_SYSTEM}]

def load_master_context():
    """Carrega e REPARA o contexto mestre – remove tool_calls órfãos."""
    global master_context
    Path(MEMORY_DIR).mkdir(exist_ok=True)
    f = Path(MASTER_MEMORY_FILE)
    if not f.exists():
        master_context = [{"role": "system", "content": MASTER_SYSTEM}]
        return

    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
        repaired = []
        i = 0
        total = len(raw)
        while i < total:
            msg = raw[i]
            if msg.get("role") != "assistant" or not msg.get("tool_calls"):
                repaired.append(msg)
                i += 1
                continue

            tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
            j = i + 1
            found_ids = set()
            while j < total and raw[j].get("role") == "tool":
                found_ids.add(raw[j].get("tool_call_id"))
                j += 1

            if tool_call_ids.issubset(found_ids):
                repaired.append(msg)
                repaired.extend(raw[i+1:j])
                i = j
            else:
                logger.warning(f"Descartando tool_calls órfãos: {tool_call_ids - found_ids}")
                i = j

        master_context[:] = repaired
        logger.info(f"Contexto mestre carregado e validado: {len(master_context)} mensagens.")
    except Exception as e:
        logger.error(f"Erro a carregar contexto mestre: {e}")
        master_context = [{"role": "system", "content": MASTER_SYSTEM}]

async def save_master_context():
    async with aiofiles.open(MASTER_MEMORY_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps(master_context[-60:], indent=2, ensure_ascii=False))

def is_owner(update: Update) -> bool:
    return update.effective_user.id == OWNER_TELEGRAM_ID

async def safe_send_message(bot, chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Envia mensagem sem causar erro de parsing de entidades."""
    if not text:
        return
    # Sanitiza: substitui triple backticks que quebram o Markdown
    if parse_mode == "Markdown":
        text = text.replace("```", "` ` `")
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Falha com {parse_mode}: {e}. Tentando sem formatação.")
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=None)
        except Exception as e2:
            logger.error(f"Erro crítico: {e2}")

async def master_respond(user_msg: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    global master_context
    master_context.append({"role": "user", "content": user_msg})

    for _ in range(20):
        resp = await client.chat.completions.create(
            model="deepseek-chat",
            messages=master_context,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=2000,
        )
        msg = resp.choices[0].message
        finish = resp.choices[0].finish_reason
        master_context.append(msg.model_dump(exclude_none=True))

        if finish == "stop" or not msg.tool_calls:
            await save_master_context()
            return msg.content or "✅ Feito."

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}
            await safe_send_message(context.bot, chat_id, f"🔧 `{name}`...")
            result = await execute_tool(name, args)
            preview = str(result)[:500]
            await safe_send_message(context.bot, chat_id, f"```\n{preview}\n```")
            master_context.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    await save_master_context()
    return "⚠️ Limite de iterações atingido."

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text(
        "🤖 *Correoto ativo — Agentes que programam de verdade.*\n\n"
        "Comandos:\n"
        "/agents — listar agentes\n"
        "/run_agent <id> <tarefa> — executar tarefa real\n"
        "/auto_start <id> — modo autónomo (age sozinho)\n"
        "/auto_stop <id> — parar modo autónomo\n"
        "/new_agent <nome> | <missão> — criar agente\n"
        "/del_agent <id> — apagar agente\n"
        "/git_status — estado do repositório\n"
        "/clear — limpar memória do mestre\n\n"
        "Ou escreve diretamente — o mestre usa ferramentas reais para agir.",
        parse_mode="Markdown"
    )

async def cmd_agents(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    agents = manager.list_agents()
    if not agents:
        await update.message.reply_text("Nenhum agente existe ainda.")
        return
    lines = ["📋 *Agentes:*"]
    for a in agents:
        icon = "🟢" if a.status == "running" else "⚪"
        lines.append(f"{icon} `{a.id[:8]}` *{a.name}* — {a.status}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_run_agent(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Uso: /run_agent <id> <tarefa>")
        return
    agent_id = ctx.args[0]
    task = " ".join(ctx.args[1:])
    chat_id = update.effective_chat.id
    await safe_send_message(ctx.bot, chat_id, f"⚙️ A executar tarefa no agente `{agent_id[:8]}`...")
    async def notify(name, args, result):
        preview = str(result)[:400]
        await safe_send_message(ctx.bot, chat_id, f"🔧 `{name}`\n```\n{preview}\n```")
    result = await manager.run_task(agent_id, task, on_tool_call=notify)
    await safe_send_message(ctx.bot, chat_id, result[:4000])

async def cmd_auto_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if not ctx.args:
        await update.message.reply_text("Uso: /auto_start <id>")
        return
    ok = await manager.start_agent(ctx.args[0], update.effective_chat.id, ctx.bot.send_message)
    if not ok:
        await update.message.reply_text("⚠️ Não foi possível iniciar (já ativo ou não existe).")

async def cmd_auto_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if not ctx.args:
        await update.message.reply_text("Uso: /auto_stop <id>")
        return
    manager.stop_agent(ctx.args[0])
    await update.message.reply_text("⏹️ Agente parado.")

async def cmd_new_agent(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    text = " ".join(ctx.args)
    if "|" not in text:
        await update.message.reply_text("Uso: /new_agent <nome> | <missão detalhada>")
        return
    name, mission = text.split("|", 1)
    a = manager.create_agent(name.strip(), mission.strip())
    await update.message.reply_text(f"✅ Agente *{a.name}* criado (`{a.id[:8]}`).", parse_mode="Markdown")

async def cmd_del_agent(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if not ctx.args:
        await update.message.reply_text("Uso: /del_agent <id>")
        return
    ok = manager.delete_agent(ctx.args[0])
    await update.message.reply_text("🗑️ Apagado." if ok else "⚠️ Não encontrado.")

async def cmd_git_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    result = await _git_status()
    await safe_send_message(ctx.bot, update.effective_chat.id, f"```\n{result[:3000]}\n```")

async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    global master_context
    master_context = [{"role": "system", "content": MASTER_SYSTEM}]
    await save_master_context()
    await update.message.reply_text("🧹 Memória limpa.")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    chat_id = update.effective_chat.id
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
    reply = await master_respond(update.message.text, chat_id, ctx)
    if reply:
        await safe_send_message(ctx.bot, chat_id, reply[:4000])

def main():
    load_master_context()
    Path(MEMORY_DIR).mkdir(exist_ok=True)
    Path("memory/agents").mkdir(parents=True, exist_ok=True)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("agents", cmd_agents))
    app.add_handler(CommandHandler("run_agent", cmd_run_agent))
    app.add_handler(CommandHandler("auto_start", cmd_auto_start))
    app.add_handler(CommandHandler("auto_stop", cmd_auto_stop))
    app.add_handler(CommandHandler("new_agent", cmd_new_agent))
    app.add_handler(CommandHandler("del_agent", cmd_del_agent))
    app.add_handler(CommandHandler("git_status", cmd_git_status))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Correoto iniciado.")
    app.run_polling()

if __name__ == "__main__":
    main()