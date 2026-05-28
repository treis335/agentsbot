"""
main.py — PONTO DE ENTRADA PRINCIPAL DO ECOSSISTEMA CORREOTO v2.0

Unifica:
- Bot Telegram (interface com o utilizador, com memória de conversa)
- API REST (para dashboard e controlo externo)
- Orquestrador (gestão do ciclo de vida)
- Gestor de agentes com memória episódica real
- Memória global/episódica/semântica persistente
- Métricas e monitorização

Uso:
    python main.py                    # Modo normal (Telegram + API)
    python main.py --no-telegram      # Apenas API
    python main.py --no-api           # Apenas Telegram
"""
import asyncio
import json
import logging
import sys
import threading
from pathlib import Path

# ─── Configuração ─────────────────────────────────────────────────────────
from core.config import Config
from core.orchestrator import Orchestrator
from core.bus import bus
from core.bus_replay import replay_pending_events, compact_old_logs

# Agentes
from agents.manager import AgentManager
from agents.models import Agent, AgentStatus

# Tarefas
from tasks.queue import TaskQueue
from tasks.models import Task, TaskStatus, TaskPriority

# Memória
from memory.global_memory import GlobalMemory
from memory.episodica import EpisodicMemory
from memory.semantica import SemanticMemory

# Segurança
from security.auditor import AuditLogger
from security.scanner import SecretScanner

# Monitorização
from monitoring.metrics import MetricsCollector
from monitoring.health import HealthChecker

# Pipelines
from pipelines.engine import PipelineEngine
# Autonomia
from autonomous_loop import AutonomousLoop, _seed_initial_backlog, load_backlog
from core.auto_reboot import start_watchdog, check_and_reboot


# API
from api.server import start_api

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level   = getattr(logging, Config.LOG_LEVEL, "INFO"),
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("correoto")

# ─── Componentes Globais ──────────────────────────────────────────────────
config            = Config
orchestrator      = Orchestrator()
agent_manager     = AgentManager()
task_queue        = TaskQueue()
global_memory     = GlobalMemory()
semantic_memory   = SemanticMemory()
metrics_collector = MetricsCollector()
audit_logger      = AuditLogger()
secret_scanner    = SecretScanner()
health_checker    = HealthChecker()
pipeline_engine   = PipelineEngine()

telegram_application = None


def init_telegram():
    global telegram_application

    if not config.TELEGRAM_BOT_TOKEN or "placeholder" in config.TELEGRAM_BOT_TOKEN:
        logger.warning("[Telegram] Token não configurado. Bot desativado.")
        return None

    try:
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
        from bot.handlers import (
            cmd_start, cmd_agents, cmd_run_agent, cmd_auto_start,
            cmd_auto_stop, cmd_new_agent, cmd_del_agent,
            cmd_git_status, cmd_clear, cmd_tasks, cmd_metrics,
            cmd_help, cmd_memory, cmd_clear_memory, handle_message,
        )

        app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

        app.add_handler(CommandHandler("start",        cmd_start))
        app.add_handler(CommandHandler("agents",       cmd_agents))
        app.add_handler(CommandHandler("run",          cmd_run_agent))
        app.add_handler(CommandHandler("run_agent",    cmd_run_agent))
        app.add_handler(CommandHandler("auto_start",   cmd_auto_start))
        app.add_handler(CommandHandler("auto_stop",    cmd_auto_stop))
        app.add_handler(CommandHandler("new_agent",    cmd_new_agent))
        app.add_handler(CommandHandler("del_agent",    cmd_del_agent))
        app.add_handler(CommandHandler("git",          cmd_git_status))
        app.add_handler(CommandHandler("git_status",   cmd_git_status))
        app.add_handler(CommandHandler("clear",        cmd_clear))
        app.add_handler(CommandHandler("tasks",        cmd_tasks))
        app.add_handler(CommandHandler("metrics",      cmd_metrics))
        app.add_handler(CommandHandler("memory",       cmd_memory))
        app.add_handler(CommandHandler("clear_memory", cmd_clear_memory))
        app.add_handler(CommandHandler("help",         cmd_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        # ── Comandos do loop autónomo ──────────────────────────────────────
        from bot.handlers import (
            cmd_auto_status, cmd_auto_pause, cmd_auto_resume,
            cmd_auto_backlog, cmd_auto_task, set_auto_loop
        )
        app.add_handler(CommandHandler("auto_status",  cmd_auto_status))
        app.add_handler(CommandHandler("pausar",       cmd_auto_pause))
        app.add_handler(CommandHandler("retomar",      cmd_auto_resume))
        app.add_handler(CommandHandler("backlog",      cmd_auto_backlog))
        app.add_handler(CommandHandler("tarefa",       cmd_auto_task))
        # ──────────────────────────────────────────────────────────────────


        telegram_application = app
        logger.info("[Telegram] Bot configurado com sucesso.")
        return app

    except ImportError as e:
        logger.warning(f"[Telegram] Erro ao importar: {e}. Bot desativado.")
    except Exception as e:
        logger.error(f"[Telegram] Erro ao inicializar: {e}")
    return None


async def main():
    args         = set(sys.argv[1:])
    no_telegram  = "--no-telegram" in args
    no_api       = "--no-api" in args

    logger.info("=" * 60)
    logger.info("  CORREOTO v2.0 - ECOSSISTEMA AUTÓNOMO DE AGENTES IA")
    logger.info(f"  Repo: {config.GITHUB_REPO}")
    logger.info(f"  Path: {config.REPO_LOCAL_PATH}")
    logger.info("=" * 60)

    warnings = config.validate()
    for w in warnings:
        logger.warning(f"  ! {w}")

    # Registar arranque na memória global
    global_memory.update_system_state("last_start", __import__("datetime").datetime.now().isoformat())
    global_memory.update_system_state("agents_count", len(agent_manager.list_agents()))

    # Batch 3 — replay de eventos não processados (crashes anteriores)
    try:
        replayed = await replay_pending_events(bus)
        if replayed:
            logger.info(f"[Bus] {replayed} evento(s) reenviado(s) do WAL")
        compact_old_logs()  # limpar logs antigos (>7 dias)
    except Exception as e:
        logger.warning(f"[Bus] Replay falhou (não crítico): {e}")

    await orchestrator.start()
    # Iniciar watchdog de auto-reboot
    start_watchdog()

    # API REST
    if not no_api:
        api_thread = threading.Thread(
            target = start_api,
            kwargs = {
                "agent_manager":     agent_manager,
                "task_queue":        task_queue,
                "global_memory":     global_memory,
                "metrics_collector": metrics_collector,
                "audit_logger":      audit_logger,
            },
            daemon = True,
        )
        api_thread.start()
        logger.info("[API] REST API em http://localhost:8080")

    # ── Iniciar o AutonomousLoop (sempre, independente do Telegram) ──────────
    _seed_initial_backlog()
    from bot.handlers import set_auto_loop
    auto_loop = AutonomousLoop(orchestrator=None, telegram_bot=None)
    loop_thread = threading.Thread(
        target=auto_loop.start,
        daemon=True,
        name="autonomous-loop",
    )
    loop_thread.start()
    logger.info("[AutonomousLoop] Loop autónomo iniciado em background.")
    # ─────────────────────────────────────────────────────────────────────────

    # Bot Telegram
    if not no_telegram:
        app = init_telegram()
        if app:
            logger.info("[Telegram] Bot a correr...")
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            logger.info("[Telegram] Bot online. A aguardar mensagens...")
            # Dar o bot ao loop para enviar relatórios Telegram
            auto_loop.telegram_bot = app.bot
            set_auto_loop(auto_loop)
            while True:
                await asyncio.sleep(1)
        else:
            logger.info("[Main] Sem Telegram. A manter API activa...")
            set_auto_loop(auto_loop)
            while True:
                await asyncio.sleep(60)
    else:
        logger.info("[Main] Modo sem Telegram. A manter serviços...")
        set_auto_loop(auto_loop)
        while True:
            await asyncio.sleep(60)
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[Main] Interrompido pelo utilizador.")
    except Exception as e:
        logger.error(f"[Main] Erro fatal: {e}", exc_info=True)