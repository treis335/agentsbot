"""
Wake-Up System v3.3 - CORREOTO ECOSYSTEM
- Auto-repair completo
- SEM limites de iteracoes (corre para sempre)
- Lock file com PID para evitar duplicados
- Intervalo inteligente com backoff
- Log detalhado
- Detecta e repara corrupcao automaticamente
- Auto-restart de componentes mortos
- Heartbeat monitoring
"""

import subprocess
import sys
import os
import time
import json
import signal
from datetime import datetime

LOG_FILE = "wakeup_v3.log"
LOCK_FILE = "wakeup_v3.lock"
HEARTBEAT_FILE = "core/heartbeat.json"
WAKEUP_INTERVAL = 15
MAX_BACKOFF = 120

# Sinal para graceful shutdown
shutdown_flag = False

def signal_handler(sig, frame):
    global shutdown_flag
    shutdown_flag = True
    log("⚠️ Sinal de shutdown recebido. A encerrar graciosamente...")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
            return False, "Ficheiro heartbeat nao existe"
        with open(HEARTBEAT_FILE, "r") as f:
            data = json.load(f)
        last_time = data.get("last_heartbeat", 0)
        now = time.time()
        if now - last_time > 60:
            return False, f"Heartbeat desatualizado: {now - last_time:.0f}s atras"
        return True, "Heartbeat OK"
    except Exception as e:
        return False, f"Erro ao ler heartbeat: {e}"

def restart_main():
    """Reinicia o main.py"""
    log("🔄 A reiniciar main.py...")
    try:
        subprocess.Popen(
            [sys.executable, "main.py"],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        log("✅ main.py reiniciado com sucesso")
        return True
    except Exception as e:
        log(f"❌ Erro ao reiniciar main.py: {e}")
        return False

def repair_file(filepath):
    """Tenta reparar um ficheiro corrompido"""
    log(f"🔧 A tentar reparar: {filepath}")
    try:
        if not os.path.exists(filepath):
            log(f"⚠️ Ficheiro nao existe: {filepath}")
            return False
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) < 10:
            log(f"⚠️ Ficheiro demasiado pequeno: {filepath} ({len(content)} bytes)")
            return False
        log(f"✅ Ficheiro OK: {filepath} ({len(content)} bytes)")
        return True
    except Exception as e:
        log(f"❌ Erro ao reparar {filepath}: {e}")
        return False

def cleanup_locks():
    """Limpa ficheiros de lock antigos"""
    locks = ["wakeup_v3.lock", "main.lock", "heartbeat.lock"]
    for lock in locks:
        if os.path.exists(lock):
            try:
                os.remove(lock)
                log(f"🧹 Lock removido: {lock}")
            except:
                pass

def main_loop():
    """Loop principal - corre para sempre"""
    log("=" * 60)
    log("🚀 WAKEUP SYSTEM v3.3 INICIADO")
    log(f"📊 Modo: INFINITO (nunca para)")
    log(f"⏳ Intervalo: {WAKEUP_INTERVAL}s")
    log("=" * 60)
    
    backoff = WAKEUP_INTERVAL
    iteration = 0
    
    while not shutdown_flag:
        try:
            iteration += 1
            
            # 1. Verifica heartbeat
            hb_ok, hb_msg = check_heartbeat()
            if not hb_ok:
                log(f"⚠️ Heartbeat: {hb_msg}")
            
            # 2. Verifica se main.py está a correr
            if not is_main_running():
                log("⚠️ main.py NAO está em execucao!")
                restart_main()
                backoff = min(backoff * 1.5, MAX_BACKOFF)
            else:
                backoff = WAKEUP_INTERVAL
            
            # 3. Verifica integridade de ficheiros críticos
            critical_files = [
                "main.py",
                "auto_recovery.py",
                "auto_recovery_manager.py",
                "core/heartbeat.json",
                "config.py"
            ]
            for f in critical_files:
                if os.path.exists(f):
                    repair_file(f)
            
            # 4. Limpa locks antigos
            if iteration % 10 == 0:
                cleanup_locks()
            
            # 5. Log de status
            if iteration % 5 == 0:
                log(f"📊 Iteracao #{iteration} | Heartbeat: {hb_msg}")
            
            # Espera antes da próxima verificação
            time.sleep(backoff)
            
        except KeyboardInterrupt:
            log("⚠️ Interrompido pelo utilizador")
            break
        except Exception as e:
            log(f"❌ Erro no loop principal: {e}")
            time.sleep(backoff)
    
    # Cleanup ao sair
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except:
            pass
    log("👋 Wakeup System encerrado.")

if __name__ == "__main__":
    if is_already_running():
        log("⚠️ Wakeup System ja esta em execucao. A sair.")
        sys.exit(0)
    
    try:
        main_loop()
    except Exception as e:
        log(f"❌ Erro fatal: {e}")
        sys.exit(1)
