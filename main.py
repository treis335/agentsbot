"""
main.py — PONTO DE ENTRADA PRINCIPAL DO ECOSSISTEMA CORREOTO v2.0

Unifica:
- Bot Telegram (interface com o utilizador)
- API REST (para dashboard e controlo externo)
- Dashboard web (interface visual)
- Orquestrador (gestao do ciclo de vida)
- Gestor de agentes
- Fila de tarefas
- Memoria global/episodica/semantica
- Metricas e monitorizacao
- Auditoria e seguranca
- Pipelines multi-agente

Uso:
    python main.py                    # Modo normal (Telegram + API + Dashboard)
    python main.py --no-telegram      # Apenas API + Dashboard
    python main.py --no-dashboard     # Apenas Telegram + API
    python main.py --no-api           # Apenas Telegram
"""
import asyncio
import json
import logging
import sys
import threading
from pathlib import Path

# ============================================================
# Configuracao inicial
# ============================================================
from core.config import Config
from core.orchestrator import Orchestrator
from core.bus import bus

# Agentes
from agents.manager import AgentManager
from agents.models import Agent, AgentStatus

# Tarefas
from tasks.queue import TaskQueue
from tasks.models import Task, TaskStatus, TaskPriority

# Memoria
from memory.global_memory import GlobalMemory
from memory.episodica import EpisodicMemory
from memory.semantica import SemanticMemory

# Seguranca
from security.auditor import AuditLogger
from security.scanner import SecretScanner

# Monitorizacao
from monitoring.metrics import MetricsCollector
from monitoring.health import HealthChecker

# Pipelines
from pipelines.engine import PipelineEngine

# API
from api.server import start_api

# Dashboard
from dashboard.server import start_dashboard

# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("correoto")

# ============================================================
# Componentes Globais
# ============================================================
config = Config
orchestrator = Orchestrator()
agent_manager = AgentManager()
task_queue = TaskQueue()
global_memory = GlobalMemory()
semantic_memory = SemanticMemory()
metrics_collector = MetricsCollector()
audit_logger = AuditLogger()
secret_scanner = SecretScanner()
health_checker = HealthChecker()
pipeline_engine = PipelineEngine()

# ============================================================
# Inicializacao do Bot Telegram (opcional)
# ============================================================
telegram_bot = None
telegram_application = None

def init_telegram():
    """Inicializa o bot Telegram."""
    global telegram_bot, telegram_application

    if not config.TELEGRAM_BOT_TOKEN or "placeholder" in config.TELEGRAM_BOT_TOKEN:
        logger.warning("[Telegram] Token nao configurado. Bot desativado.")
        return

    try:
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

        # Importar handlers do modulo telegram_bot
        from bot.handlers import (
            cmd_start, cmd_agents, cmd_run_agent, cmd_auto_start,
            cmd_auto_stop, cmd_new_agent, cmd_del_agent,
            cmd_git_status, cmd_clear, cmd_tasks, cmd_metrics,
            cmd_help, handle_message,
        )

        app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

        # Registar comandos
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("agents", cmd_agents))
        app.add_handler(CommandHandler("run_agent", cmd_run_agent))
        app.add_handler(CommandHandler("auto_start", cmd_auto_start))
        app.add_handler(CommandHandler("auto_stop", cmd_auto_stop))
        app.add_handler(CommandHandler("new_agent", cmd_new_agent))
        app.add_handler(CommandHandler("del_agent", cmd_del_agent))
        app.add_handler(CommandHandler("git_status", cmd_git_status))
        app.add_handler(CommandHandler("clear", cmd_clear))
        app.add_handler(CommandHandler("tasks", cmd_tasks))
        app.add_handler(CommandHandler("metrics", cmd_metrics))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        telegram_application = app
        logger.info("[Telegram] Bot configurado com sucesso.")
        return app

    except ImportError as e:
        logger.warning(f"[Telegram] Erro ao importar: {e}. Bot desativado.")
    except Exception as e:
        logger.error(f"[Telegram] Erro ao inicializar: {e}")

# ============================================================
# Main
# ============================================================

async def main():
    """Funcao principal."""
    # Parse de argumentos
    args = set(sys.argv[1:])
    no_telegram = "--no-telegram" in args
    no_dashboard = "--no-dashboard" in args
    no_api = "--no-api" in args

    logger.info("=" * 60)
    logger.info("  CORREOTO v2.0 - ECOSSISTEMA AUTONOMO DE AGENTES IA")
    logger.info(f"  Repo: {config.GITHUB_REPO}")
    logger.info(f"  Path: {config.REPO_LOCAL_PATH}")
    logger.info("=" * 60)

    # Validar config
    warnings = config.validate()
    for w in warnings:
        logger.warning(f"  ! {w}")

    # Iniciar orquestrador
    await orchestrator.start()

    # Iniciar API REST (numa thread separada)
    api_thread = None
    if not no_api:
        api_thread = threading.Thread(
            target=start_api,
            kwargs={
                "agent_manager": agent_manager,
                "task_queue": task_queue,
                "global_memory": global_memory,
                "metrics_collector": metrics_collector,
                "audit_logger": audit_logger,
            },
            daemon=True,
        )
        api_thread.start()
        logger.info("[API] REST API em http://localhost:8080")

    # Iniciar Dashboard web (numa thread separada)
    dashboard_thread = None
    if not no_dashboard:
        dashboard_thread = threading.Thread(
            target=start_dashboard,
            daemon=True,
        )
        dashboard_thread.start()
        logger.info("[Dashboard] Web UI em http://localhost:3000")

    # Iniciar Bot Telegram
    if not no_telegram:
        app = init_telegram()
        if app:
            logger.info("[Telegram] Bot a correr...")
            # Iniciar o bot de forma async (compativel com event loop ja existente)
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            logger.info("[Telegram] Bot online. A aguardar mensagens...")
            # Manter vivo
            while True:
                await asyncio.sleep(1)
        else:
            logger.info("[Telegram] Bot nao disponivel. A manter API + Dashboard.")
            # Manter vivo
            while True:
                await asyncio.sleep(60)
    else:
        # Manter vivo sem Telegram
        logger.info("[Main] Modo sem Telegram. A manter servicos...")
        while True:
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[Main] Interrompido pelo utilizador.")
    except Exception as e:
        logger.error(f"[Main] Erro fatal: {e}", exc_info=True)
