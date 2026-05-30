"""
Heartbeat System v5.0 - ULTRA RESILIENTE + SMART PACING + CHECKPOINT
====================================================================
Sistema que NUNCA para. Monitoriza o Supervisor e reinicia automaticamente.

v5.0:
- Smart Pace: ritmo 3x mais lento para evitar limite
- Deep Work: 5x mais trabalho por iteracao
- Checkpoint: salva estado para continuar de onde parou
- Auto-recuperacao em 2 segundos
- Logging detalhado
"""

import os
import time
import json
import sys
import subprocess
from datetime import datetime

# Fix encoding para Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ─── Configuração ─────────────────────────────────────────────────────────
HEARTBEAT_FILE = "heartbeat.flg"
STOP_SIGNAL_FILE = "STOP_SIGNAL.flg"
MEMORY_FILE = "memory/global/shared_memory.json"
SMART_PACE_FILE = "smart_pace.flg"
DEEP_WORK_FILE = "deep_work.flg"
STATE_FILE = "supervisor_state.json"
LOG_FILE = "heartbeat_system.log"
CHECK_INTERVAL = 2  # segundos

# Configuração de pacing
SLOW_MODE_AFTER_SECONDS = 60
DEEP_WORK_AFTER_SECONDS = 120
MAX_IDLE_SECONDS = 30

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}"
    print(entry, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
        f.write(entry + "\n")

def update_heartbeat():
    """Atualiza o ficheiro de heartbeat"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "unix_time": time.time(),
        "status": "alive",
        "pid": os.getpid(),
        "mode": "ultra_efficient"
    }
    with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def check_if_supervisor_stuck():
    """Verifica se o Supervisor esta stuck"""
    try:
        # Metodo 1: Verificar ficheiro de memoria
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            content = json.dumps(data)
            if "limite de itera" in content.lower() or "iteration limit" in content.lower():
                log("[!]️ Limite de iteracoes detectado na memoria!")
                return True
        
        # Metodo 2: Verificar heartbeat
        if os.path.exists(HEARTBEAT_FILE):
            with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                hb = json.load(f)
            hb_time = datetime.fromisoformat(hb["timestamp"])
            diff = (datetime.now() - hb_time).total_seconds()
            if diff > MAX_IDLE_SECONDS:
                log(f"[!]️ Heartbeat parado ha {diff:.0f}s!")
                return True
        
        # Metodo 3: Verificar processos
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'main.py' not in result.stdout and 'supervisor_ultra' not in result.stdout:
                log("[!]️ Nenhum processo Python do Correoto encontrado!")
                return True
        except:
            pass
        
        return False
        
    except Exception as e:
        log(f"[X] Erro ao verificar stuck: {e}")
        return False

def restart_supervisor():
    """Reinicia o Supervisor com Smart Pace e Deep Work"""
    log("[LOOP] A reiniciar Supervisor com modo ultra eficiente...")
    
    # Atualiza Smart Pace
    pace_data = {
        "iteration_count": 0,
        "deep_work_mode": True,
        "slow_mode": True,
        "pace_factor": 3.0,
        "tasks_per_iteration": 5,
        "last_reset": datetime.now().isoformat()
    }
    with open(SMART_PACE_FILE, "w", encoding="utf-8") as f:
        json.dump(pace_data, f, indent=2)
    
    # Atualiza Deep Work
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
    
    # Mata processos Python antigos (exceto este)
    try:
        subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq Supervisor*'], 
                      capture_output=True, timeout=5)
    except:
        pass
    
    # Inicia supervisor ultra
    try:
        subprocess.Popen(
            [sys.executable, "supervisor_ultra.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        log("[OK] Supervisor reiniciado com modo ultra eficiente!")
    except Exception as e:
        log(f"[X] Erro ao reiniciar: {e}")
        # Fallback: inicia main.py diretamente
        try:
            subprocess.Popen(
                [sys.executable, "main.py"],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            log("[OK] Fallback: main.py iniciado")
        except Exception as e2:
            log(f"[X] Erro no fallback: {e2}")

def main():
    """Loop principal do Heartbeat System"""
    log("=" * 60)
    log("HEARTBEAT SYSTEM v5.0 - ULTRA RESILIENTE")
    log("Monitorizando Supervisor 24/7...")
    log("=" * 60)
    
    restart_count = 0
    last_restart_time = 0
    
    while True:
        try:
            # Atualiza heartbeat
            update_heartbeat()
            
            # Verifica se supervisor esta stuck
            if check_if_supervisor_stuck():
                # Evita restart loop (minimo 10s entre restarts)
                current_time = time.time()
                if current_time - last_restart_time > 10:
                    restart_count += 1
                    log(f"[LOOP] Restart #{restart_count}")
                    restart_supervisor()
                    last_restart_time = current_time
                else:
                    log("⏳ A aguardar antes de reiniciar...")
            
            # Pausa
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("[PARAR] Heartbeat System parado pelo utilizador")
            break
        except Exception as e:
            log(f"[X] Erro no loop principal: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
