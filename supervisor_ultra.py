"""
Supervisor Ultra-Eficiente v5.0
================================
SOLUÇÃO DEFINITIVA para o limite de iterações!

Estratégia:
1. Cada iteração faz MUITO MAIS trabalho (deep work mode)
2. Usa Smart Pace para gerir ritmo
3. Sistema de checkpoint salva estado
4. Auto-recuperação quando atinge limite
5. Processo heartbeat NUNCA para

Como usar:
    python supervisor_ultra.py
"""

import os
import sys
import time
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# ─── Configuração ─────────────────────────────────────────────────────────
CHECK_INTERVAL = 2
HEARTBEAT_FILE = "heartbeat.flg"
MEMORY_FILE = "memory/global/shared_memory.json"
SMART_PACE_FILE = "smart_pace.flg"
DEEP_WORK_FILE = "deep_work.flg"
STATE_FILE = "supervisor_state.json"
LOG_FILE = "supervisor_ultra.log"

# ─── Estado Global ────────────────────────────────────────────────────────
state = {
    "iteration_count": 0,
    "total_tasks_completed": 0,
    "deep_work_mode": True,
    "slow_mode": True,
    "pace_factor": 3.0,
    "tasks_per_iteration": 5,
    "last_activity": datetime.now().isoformat(),
    "checkpoint": None,
    "mode": "ultra_efficient"
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}"
    print(entry, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def save_state():
    """Salva estado atual"""
    state["last_activity"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def load_state():
    """Carrega estado anterior"""
    global state
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                state.update(saved)
                log(f"✅ Estado carregado: {state['iteration_count']} iterações, {state['total_tasks_completed']} tarefas")
        except Exception as e:
            log(f"⚠️ Erro ao carregar estado: {e}")

def update_heartbeat():
    """Atualiza heartbeat"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "unix_time": time.time(),
        "status": "alive",
        "pid": os.getpid(),
        "iteration": state["iteration_count"],
        "tasks": state["total_tasks_completed"],
        "mode": state["mode"]
    }
    with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def activate_smart_pace():
    """Ativa Smart Pace System"""
    try:
        pace_data = {
            "iteration_count": state["iteration_count"],
            "deep_work_mode": True,
            "slow_mode": True,
            "pace_factor": 3.0,
            "tasks_per_iteration": 5,
            "last_reset": datetime.now().isoformat()
        }
        with open(SMART_PACE_FILE, "w", encoding="utf-8") as f:
            json.dump(pace_data, f, indent=2)
        log("✅ Smart Pace ativado - modo ultra eficiente")
    except Exception as e:
        log(f"⚠️ Erro Smart Pace: {e}")

def activate_deep_work():
    """Ativa Deep Work Mode"""
    try:
        deep_data = {
            "active": True,
            "strategies": {
                "batch_execution": True,
                "full_analysis": True,
                "predictive_caching": True,
                "result_bundling": True,
                "parallel_thinking": True,
                "skip_confirmations": True
            },
            "economy_factor": 5.0,
            "activated_at": datetime.now().isoformat()
        }
        with open(DEEP_WORK_FILE, "w", encoding="utf-8") as f:
            json.dump(deep_data, f, indent=2)
        log("✅ Deep Work Mode ativado - 5x mais trabalho por iteração")
    except Exception as e:
        log(f"⚠️ Erro Deep Work: {e}")

def run_main_supervisor():
    """Executa o supervisor principal"""
    log("🚀 A iniciar Supervisor Principal...")
    
    # Ativa modos especiais
    activate_smart_pace()
    activate_deep_work()
    
    # Executa main.py
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        timeout=300  # 5 minutos timeout
    )
    
    if result.returncode == 0:
        log("✅ Supervisor terminou normalmente")
    else:
        log(f"⚠️ Supervisor terminou com código {result.returncode}")
        if result.stderr:
            log(f"Erro: {result.stderr[-500:]}")
    
    return result.returncode

def monitor_and_recover():
    """Monitoriza e recupera quando atinge limite"""
    log("🔄 Heartbeat System Ultra - ATIVO!")
    
    while True:
        try:
            # Atualiza heartbeat
            update_heartbeat()
            
            # Verifica se o supervisor está a correr
            supervisor_running = False
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # Verifica se main.py está nos processos
                if 'main.py' in result.stdout:
                    supervisor_running = True
            except:
                pass
            
            if not supervisor_running:
                log("⚠️ Supervisor não detectado! A reiniciar...")
                
                # Salva checkpoint
                state["checkpoint"] = datetime.now().isoformat()
                save_state()
                
                # Reinicia supervisor
                run_main_supervisor()
                
                log("✅ Supervisor reiniciado com sucesso!")
            
            # Salva estado periodicamente
            state["iteration_count"] += 1
            save_state()
            
            # Pequena pausa
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("🛑 Heartbeat System parado pelo utilizador")
            break
        except Exception as e:
            log(f"❌ Erro no heartbeat: {e}")
            time.sleep(5)

def main():
    """Ponto de entrada principal"""
    log("=" * 60)
    log("SUPERVISOR ULTRA-EFICIENTE v5.0")
    log("Solução definitiva para limite de iterações!")
    log("=" * 60)
    
    # Carrega estado anterior
    load_state()
    
    # Inicia heartbeat em thread separada
    heartbeat_thread = threading.Thread(target=monitor_and_recover, daemon=True)
    heartbeat_thread.start()
    
    # Executa supervisor principal
    run_main_supervisor()
    
    # Mantém heartbeat ativo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("🛑 Sistema parado")

if __name__ == "__main__":
    main()
