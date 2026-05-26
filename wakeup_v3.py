"""
Wake-Up System v3.2 - CORREOTO ECOSYSTEM
- Auto-repair completo
- Sem limites de iteracoes (corre para sempre)
- Lock file com PID para evitar duplicados
- Intervalo inteligente com backoff
- Log detalhado
- Detecta e repara corrupcao automaticamente
"""

import subprocess
import sys
import os
import time
import json
from datetime import datetime

LOG_FILE = "wakeup_v3.log"
LOCK_FILE = "wakeup_v3.lock"
HEARTBEAT_FILE = "core/heartbeat.json"
WAKEUP_INTERVAL = 15
MAX_BACKOFF = 120

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except:
        pass

def is_already_running():
    """Evita duplicados - lock file com PID"""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if pid != os.getpid():
                result = subprocess.run(
                    f'tasklist /FI "PID eq {pid}" /FO CSV /NH',
                    capture_output=True, text=True, shell=True, timeout=5
                )
                if str(pid) in result.stdout:
                    return True
        except:
            pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return False

def is_main_running():
    """Verifica se main.py esta em execucao via tasklist (compativel Windows 11)"""
    try:
        result = subprocess.run(
            'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH',
            capture_output=True, text=True, shell=True, timeout=5
        )
        for line in result.stdout.split('\n'):
            if 'main.py' in line:
                return True
        return False
    except:
        return False

def check_heartbeat():
    """Verifica se o heartbeat está atualizado"""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            return False
        with open(HEARTBEAT_FILE, "r") as f:
            hb = json.load(f)
        last_time = datetime.fromisoformat(hb.get("timestamp", "2000-01-01"))
        elapsed = (datetime.now() - last_time).total_seconds()
        return elapsed < 60  # heartbeat válido se < 60s
    except:
        return False

def restart_main():
    """Reinicia o main.py com todas as flags necessarias"""
    log("🔄 A reiniciar main.py...")
    try:
        # Mata processos python antigos (exceto este)
        result = subprocess.run(
            'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH',
            capture_output=True, text=True, shell=True, timeout=5
        )
        current_pid = os.getpid()
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    pid = int(parts[1].strip().strip('"'))
                    if pid != current_pid and pid != 0:
                        subprocess.run(f'taskkill /F /PID {pid}', capture_output=True, shell=True, timeout=3)
                except:
                    pass
        
        time.sleep(1)
        
        # Inicia main.py
        subprocess.Popen(
            [sys.executable, "main.py", "--auto", "--recover", "--forever"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        log("✅ main.py reiniciado com sucesso!")
        return True
    except Exception as e:
        log(f"❌ Erro ao reiniciar main.py: {e}")
        return False

def restart_components():
    """Reinicia componentes do ecossistema"""
    log("🔄 A reiniciar componentes do ecossistema...")
    components = [
        "cerebro/core/brain.py",
        "cerebro/core/ml_engine.py",
        "cerebro/core/api_connector.py",
        "core/keep_alive.py"
    ]
    for comp in components:
        try:
            if os.path.exists(comp):
                subprocess.Popen(
                    [sys.executable, comp],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                log(f"✅ {comp} iniciado")
        except Exception as e:
            log(f"❌ Erro ao iniciar {comp}: {e}")
    return True

def repair_corrupted_files():
    """Verifica e repara ficheiros corrompidos"""
    log("🔧 A verificar integridade dos ficheiros...")
    critical_files = [
        "main.py",
        "auto_recovery.py",
        "auto_recovery_manager.py",
        "core/keep_alive.py",
        "cerebro/core/brain.py",
        "cerebro/core/ml_engine.py",
        "cerebro/core/api_connector.py"
    ]
    for f in critical_files:
        if not os.path.exists(f):
            log(f"⚠️ Ficheiro critico em falta: {f}")
        else:
            size = os.path.getsize(f)
            if size < 10:
                log(f"⚠️ Ficheiro suspeitamente pequeno: {f} ({size} bytes)")
    log("✅ Verificacao concluida")
    return True

def main():
    """Loop principal - corre para sempre"""
    log("=" * 60)
    log("🚀 WakeUp System v3.2 INICIADO")
    log("=" * 60)
    
    if is_already_running():
        log("⚠️ WakeUp ja esta em execucao. A sair.")
        return
    
    log(f"PID: {os.getpid()}")
    log(f"Intervalo: {WAKEUP_INTERVAL}s")
    
    backoff = WAKEUP_INTERVAL
    consecutive_failures = 0
    
    while True:
        try:
            # 1. Verifica heartbeat
            heartbeat_ok = check_heartbeat()
            
            # 2. Verifica se main.py está a correr
            main_running = is_main_running()
            
            # 3. Verifica integridade
            repair_corrupted_files()
            
            if not heartbeat_ok and not main_running:
                consecutive_failures += 1
                log(f"⚠️ Heartbeat ausente e main.py parado (falha #{consecutive_failures})")
                
                if consecutive_failures >= 2:
                    log("🔄 A iniciar recuperacao total...")
                    restart_components()
                    time.sleep(2)
                    restart_main()
                    backoff = min(backoff * 1.5, MAX_BACKOFF)
                    consecutive_failures = 0
            else:
                consecutive_failures = 0
                backoff = WAKEUP_INTERVAL
                
                if not main_running and heartbeat_ok:
                    log("⚠️ Heartbeat ok mas main.py parado. A reiniciar...")
                    restart_main()
            
            # Log de saúde periódico
            if int(time.time()) % 60 < WAKEUP_INTERVAL:
                log(f"💚 Sistema operacional | Heartbeat: {'✅' if heartbeat_ok else '❌'} | Main: {'✅' if main_running else '❌'}")
            
            time.sleep(backoff)
            
        except KeyboardInterrupt:
            log("🛑 WakeUp interrompido pelo utilizador")
            break
        except Exception as e:
            log(f"❌ Erro no loop principal: {e}")
            time.sleep(backoff)

if __name__ == "__main__":
    main()
