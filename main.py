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
import os
import sys
import threading
from pathlib import Path

# ============================================================
# FIX #1: Correção de encoding UTF-8 (ANTES de qualquer print/log)
# ============================================================
# Importa fix_encoding PRIMEIRO para substituir print() globalmente
# e configurar PYTHONIOENCODING=utf-8 antes de qualquer output.
# Isto previne UnicodeEncodeError com emojis no Windows.
import fix_encoding  # noqa: F401

# ============================================================
# FIX #2: Instance Lock (evita múltiplas instâncias)
# ============================================================
_INSTANCE_LOCK_FILE = Path(__file__).parent / ".instance.lock"

def _check_instance_lock():
    if _INSTANCE_LOCK_FILE.exists():
        try:
            pid = int(_INSTANCE_LOCK_FILE.read_text().strip())
            if os.name == "nt":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x0400, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    print(f"[LOCK] Outra instancia (PID {pid}) ja ativa. A sair.")
                    sys.exit(0)
            else:
                try:
                    os.kill(pid, 0)
                    print(f"[LOCK] Outra instancia (PID {pid}) ja ativa. A sair.")
                    sys.exit(0)
                except OSError:
                    pass
        except (ValueError, OSError):
            pass
    _INSTANCE_LOCK_FILE.write_text(str(os.getpid()))

# Forcar UTF-8 no stdout/stderr para evitar UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_check_instance_lock()

# --- Correção de Encoding + Supressão de Logs Telegram ---
from utils import force_utf8, suppress_telegram_errors
force_utf8()
suppress_telegram_errors()

# --- Configuração ---------------------------------------------------------
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

# --- Logging ----------------------------------------------------------------
logging.basicConfig(
    level   = getattr(logging, Config.LOG_LEVEL, "INFO"),
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("correoto")

# --- Componentes Globais --------------------------------------------------
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
        logger.warning("[Telegram] Token n?o configurado. Bot desativado.")
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
        # -- Comandos do loop autónomo --------------------------------------
        from bot.handlers import (
            cmd_auto_status, cmd_auto_pause, cmd_auto_resume,
            cmd_auto_backlog, cmd_auto_task, set_auto_loop
        )
        app.add_handler(CommandHandler("auto_status",  cmd_auto_status))
        app.add_handler(CommandHandler("pausar",       cmd_auto_pause))
        app.add_handler(CommandHandler("retomar",      cmd_auto_resume))
        app.add_handler(CommandHandler("backlog",      cmd_auto_backlog))
        app.add_handler(CommandHandler("tarefa",       cmd_auto_task))
        # ------------------------------------------------------------------


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
    logger.info("  CORREOTO v2.0 - ECOSSISTEMA AUT?NOMO DE AGENTES IA")
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
        logger.warning(f"[Bus] Replay falhou (n?o cr?tico): {e}")

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

    # -- Iniciar o AutonomousLoop (sempre, independente do Telegram) ----------
    _seed_initial_backlog()
    from bot.handlers import set_auto_loop
    auto_loop = AutonomousLoop(orchestrator=None, telegram_bot=None)
    loop_thread = threading.Thread(
        target=auto_loop.start,
        daemon=True,
        name="autonomous-loop",
    )
    loop_thread.start()
    logger.info("[AutonomousLoop] Loop aut?nomo iniciado em background.")
    # -------------------------------------------------------------------------

    # Bot Telegram
    if not no_telegram:
        app = init_telegram()
        if app:
            # Lock Telegram: garantir que apenas uma instancia faz polling
            if not acquire_telegram_lock():
                logger.warning("[Telegram] Outra instancia ja ativa. A encerrar esta.")
                return  # ← FIX: sair em vez de ficar em loop
            logger.info("[Telegram] Bot a correr...")
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            logger.info("[Telegram] Bot online. A aguardar mensagens...")
            # Dar o bot ao loop para enviar relatórios Telegram
            auto_loop.telegram_bot = app.bot
            set_auto_loop(auto_loop)

            # Ligar o Notifier ao bot real
            try:
                from bot.notifier import get_notifier
                from core.config import Config
                owner_id = getattr(Config, "OWNER_TELEGRAM_ID", None)
                if owner_id:
                    notifier = get_notifier()
                    notifier.set_bot(app.bot, int(owner_id))
                    await notifier.system_started()
                    logger.info("[Notifier] Notifica??es proactivas activas")
            except Exception as e:
                logger.warning(f"[Notifier] Falhou ao iniciar: {e}")
            while True:
                await asyncio.sleep(1)
        else:
            logger.info("[Main] Sem Telegram. A manter API activa...")
            set_auto_loop(auto_loop)
            while True:
                await asyncio.sleep(60)
    else:
        logger.info("[Main] Modo sem Telegram. Sistema autonomo a correr...")
        set_auto_loop(auto_loop)
        # Keepalive — o loop autonomo corre em daemon thread, precisamos manter o processo vivo
        logger.info("[Main] Sistema activo. Ctrl+C para sair.")
        while True:
            await asyncio.sleep(60)
    # (fim da função main)
# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from lock_utils import acquire_lock, release_lock
    from telegram_lock import acquire_telegram_lock, release_telegram_lock
    if not acquire_lock():
        sys.exit("Outra instancia ja esta a correr. A encerrar.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[Main] Interrompido pelo utilizador.")
    except Exception as e:
        logger.error(f"[Main] Erro fatal: {e}", exc_info=True)
    finally:
        try:
            release_telegram_lock()
        except Exception:
            pass
        try:
            release_lock()
        except Exception:
            pass
