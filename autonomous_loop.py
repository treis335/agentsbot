"""
autonomous_loop.py
Motor de autonomia do ecossistema — ciclo autónomo, watchdog, cognição.
"""

import json
import os
import sys
import time
import threading
import random
from datetime import datetime
from pathlib import Path

# ─── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────
CYCLE_INTERVAL_SECONDS = 10
MAX_TASKS_PER_CYCLE = 1
MEMORY_DIR = Path("memory")
BACKLOG_FILE = MEMORY_DIR / "backlog.json"
LOG_FILE = MEMORY_DIR / "autonomous_log.md"
REBOOT_FLAG = "auto_reboot.flag"


# ─── BACKLOG ───────────────────────────────────────────────────────────────────
def load_backlog() -> list:
    MEMORY_DIR.mkdir(exist_ok=True)
    if not BACKLOG_FILE.exists():
        return []
    try:
        with open(BACKLOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_backlog(backlog: list):
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(BACKLOG_FILE, "w", encoding="utf-8") as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)


def _seed_initial_backlog():
    """Cria backlog inicial se não existir"""
    MEMORY_DIR.mkdir(exist_ok=True)
    if not BACKLOG_FILE.exists():
        initial = [
            {"id": "onboarding", "desc": "Configurar ambiente inicial do agente", "status": "pending"},
            {"id": "self_check", "desc": "Verificar saude do sistema e dependencias", "status": "pending"},
            {"id": "first_task", "desc": "Executar primeira tarefa de teste", "status": "pending"}
        ]
        save_backlog(initial)
        print("[Seed] Backlog inicial criado")


# ─── LOG ───────────────────────────────────────────────────────────────────────
def log_cycle(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── CLASSE PRINCIPAL ─────────────────────────────────────────────────────────
class AutonomousLoop:
    def __init__(self, orchestrator=None, telegram_bot=None):
        self.orchestrator = orchestrator
        self.telegram_bot = telegram_bot
        self.running = False
        self.thread = None
        self.cycle_count = 0

    def start(self):
        """Inicia o loop autonomo em background"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="AutonomousLoop"
        )
        self.thread.start()
        log_cycle("AutonomousLoop iniciado em background")

    def stop(self):
        """Para o loop"""
        self.running = False
        log_cycle("AutonomousLoop parado")

    def _run_loop(self):
        """Loop principal — corre para sempre"""
        log_cycle("=" * 50)
        log_cycle("LOOP AUTONOMO INICIADO")
        log_cycle(f"Ciclo a cada {CYCLE_INTERVAL_SECONDS}s")
        log_cycle("=" * 50)

        while self.running:
            try:
                self._run_cycle()
            except Exception as e:
                log_cycle(f"[ERRO] No ciclo: {e}")
            time.sleep(CYCLE_INTERVAL_SECONDS)

    def _run_cycle(self):
        """Um ciclo completo do loop autonomo"""
        self.cycle_count += 1
        cycle_id = self.cycle_count
        log_cycle(f"[Ciclo #{cycle_id}] Inicio")

        # 1. Verificar reboot
        if os.path.exists(REBOOT_FLAG):
            log_cycle("[REBOOT] Sinal detetado! A reiniciar...")
            try:
                os.remove(REBOOT_FLAG)
            except:
                pass
            time.sleep(0.5)
            os.execv(sys.executable, [sys.executable, "main.py"])
            return

        # 2. Carregar backlog
        backlog = load_backlog()
        if not backlog:
            log_cycle("[Ciclo] Backlog vazio — nada a fazer")
            return

        # 3. Filtrar tarefas pendentes
        pending = [t for t in backlog if t.get("status") == "pending"]
        if not pending:
            log_cycle("[Ciclo] Nenhuma tarefa pendente")
            return

        # 4. Escolher tarefa (prioridade ou primeira)
        task = pending[0]
        task_id = task.get("id", "unknown")
        task_desc = task.get("desc", task.get("task", task.get("title", "Tarefa sem nome")))
        log_cycle(f"[Ciclo] Tarefa: {task_id} — {task_desc}")

        # 5. Executar (placeholder — futuramente chamar orquestrador)
        log_cycle(f"[Ciclo] A executar tarefa...")

        # 6. Marcar como concluida
        for t in backlog:
            if t.get("id") == task_id:
                t["status"] = "completed"
                t["completed_at"] = datetime.now().isoformat()
                break

        save_backlog(backlog)
        log_cycle(f"[Ciclo #{cycle_id}] Tarefa concluida: {task_desc}")
