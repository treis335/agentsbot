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
# Isto previne UnicodeEncodeError com emojis (🚀🔧✅❌🔄) no Windows.
import fix_encoding  # noqa: F401 — aplica correção automaticamente

# ============================================================
# FIX: Instance Lock
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
from monit