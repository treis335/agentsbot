"""
autonomous_loop.py
Motor de autonomia do ecossistema Correoto.
Ciclo rapido (10s), watchdog de reboot, integrado com memoria e grounding.
"""

import json
import os
import sys
import time
import random
from datetime import datetime
from pathlib import Path

# ─── CONFIGURACAO ──────────────────────────────────────────────────────────────

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
    with open(BACKLOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_backlog(backlog: list):
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(BACKLOG_FILE, "w", encoding="utf-8") as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)

# ─── LOG ───────────────────────────────────────────────────────────────────────

def log_cycle(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ─── CHECKPOINT ────────────────────────────────────────────────────────────────

def save_checkpoint(cycle: int, task_id: str, status: str):
    cp_file = MEMORY_DIR / "checkpoint.json"
    data = {
        "last_cycle": cycle,
        "last_task": task_id,
        "last_status": status,
        "timestamp": datetime.now().isoformat()
    }
    with open(cp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ─── CICLO PRINCIPAL ───────────────────────────────────────────────────────────

def run_cycle(cycle_number: int):
    """Executa um ciclo de trabalho autonomo."""
    
    # 1. Verificar reboot flag
    if os.path.exists(REBOOT_FLAG):
        log_cycle(f"REBOOT FLAG DETETADO no ciclo #{cycle_number}")
        os.remove(REBOOT_FLAG)
        log_cycle("A REINICIAR SISTEMA...")
        time.sleep(0.5)
        os.execv(sys.executable, [sys.executable, "main.py"])
        return
    
    # 2. Carregar backlog
    backlog = load_backlog()
    pending = [t for t in backlog if t.get("status") == "pending"]
    
    if not pending:
        log_cycle(f"Ciclo #{cycle_number}: 0 tarefas pendentes. A dormir {CYCLE_INTERVAL_SECONDS}s...")
        return
    
    # 3. Pegar proxima tarefa
    task = pending[0]
    task_id = task.get("id", "unknown")
    task_desc = task.get("desc", "sem descricao")
    
    log_cycle(f"Ciclo #{cycle_number}: A trabalhar em '{task_id}' - {task_desc[:60]}")
    save_checkpoint(cycle_number, task_id, "processing")
    
    # 4. Marcar como processing
    for t in backlog:
        if t.get("id") == task_id:
            t["status"] = "processing"
    save_backlog(backlog)
    
    # 5. Executar a tarefa (simulacao - o Supervisor real faz isto)
    # Neste ciclo, apenas registamos que estamos a trabalhar
    log_cycle(f"  -> A executar: {task_desc}")
    
    # 6. Marcar como done
    for t in backlog:
        if t.get("id") == task_id:
            t["status"] = "done"
    save_backlog(backlog)
    
    log_cycle(f"  -> Concluida: {task_id}")
    save_checkpoint(cycle_number, task_id, "done")

# ─── MAIN LOOP ─────────────────────────────────────────────────────────────────

def main_loop():
    log_cycle("=" * 50)
    log_cycle("LOOP AUTONOMO INICIADO")
    log_cycle(f"Ciclo a cada {CYCLE_INTERVAL_SECONDS}s")
    log_cycle("=" * 50)
    
    cycle = 0
    while True:
        cycle += 1
        try:
            run_cycle(cycle)
        except Exception as e:
            log_cycle(f"ERRO no ciclo #{cycle}: {e}")
        
        time.sleep(CYCLE_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()
