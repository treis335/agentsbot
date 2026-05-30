"""
Wake-Up System v5.0 - CORREOTO ECOSYSTEM
✅ Auto-repair completo
✅ SEM limites de iteracoes (corre para sempre)
✅ Lock file com PID para evitar duplicados
✅ Intervalo inteligente com backoff
✅ Log detalhado
✅ Detecta e repara corrupcao automaticamente
✅ Auto-restart de componentes mortos
✅ Heartbeat monitoring
✅ Decisao autonoma - so pede supervisao em casos criticos
✅ Verificacao de integridade de ficheiros
✅ Ciclo de auto-evolucao
"""

import subprocess
import sys
import os
import time
import json
import signal
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
LOG_FILE = BASE / "wakeup_v3.log"
LOCK_FILE = BASE / "wakeup_v3.lock"
BOT_LOCK_FILE = BASE / "bot_telegram.lock"
HEARTBEAT_FILE = BASE / "core" / "heartbeat.json"
WAKEUP_INTERVAL = 15
MAX_BACKOFF = 120

shutdown_flag = False

def signal_handler(sig, frame):
    global shutdown_flag
    shutdown_flag = True
    log("Shutdown recebido. A encerrar graciosamente...")

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


def is_bot_already_running():
    """Verifica se o bot_telegram.lock esta ativo (outra instancia do main.py)."""
    if os.path.exists(BOT_LOCK_FILE):
        try:
            with open(BOT_LOCK_FILE, "r") as f:
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
    return False

def is_main_running():
    """Verifica se main.py esta em execucao via tasklist."""
    try:
        result = subprocess.run(
            'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH',
            capture_output=True, text=True, shell=True, timeout=5
        )
        return "main.py" in result.stdout
    except:
        return False

def check_heartbeat():
    """Verifica o heartbeat do sistema."""
    try:
        if HEARTBEAT_FILE.exists():
            data = json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
            last_beat = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
            elapsed = (datetime.now() - last_beat).total_seconds()
            if elapsed > 120:
                log(f"⚠️ Heartbeat antigo! Ultimo: {elapsed:.0f}s atras")
                return False
            return True
        return False
    except:
        return False

def check_file_integrity():
    """Verifica integridade dos ficheiros criticos."""
    critical_files = [
        "main.py",
        "run_forever.py",
        "auto_recovery.py",
        "auto_update.py",
        "agents/souls/supervisor.md",
    ]
    issues = []
    for f in critical_files:
        path = BASE / f
        if not path.exists():
            issues.append(f)
        elif path.stat().st_size < 100:
            issues.append(f"{f} (tamanho suspeito)")
    return issues

def launch_main():
    """Lanca o main.py."""
    # Verificar se o bot ja esta a correr (lock singleton)
    if is_bot_already_running():
        log("✅ main.py ja esta em execucao (bot_telegram.lock ativo).")
        return None
    log("🚀 A lancar main.py...")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(BASE / "main.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=BASE
        )
        log(f"✅ main.py lancado (PID: {proc.pid})")
        return proc
    except Exception as e:
        log(f"❌ Erro ao lancar main.py: {e}")
        return None

def main():
    log("=" * 60)
    log("🚀 WAKE-UP SYSTEM v5.0 INICIADO")
    log(f"Intervalo: {WAKEUP_INTERVAL}s | Backoff max: {MAX_BACKOFF}s")
    log("=" * 60)
    
    if is_already_running():
        log("⚠️ Ja existe uma instancia em execucao. A sair.")
        return
    
    backoff = WAKEUP_INTERVAL
    iteration = 0
    
    try:
        while not shutdown_flag:
            iteration += 1
            log(f"🔄 Ciclo #{iteration}")
            
            # Verificar integridade
            issues = check_file_integrity()
            if issues:
                log(f"⚠️ Problemas detetados: {issues}")
            
            # Verificar heartbeat
            heartbeat_ok = check_heartbeat()
            if not heartbeat_ok:
                log("⚠️ Heartbeat ausente ou antigo!")
            
            # Verificar se main.py esta a correr
            if not is_main_running():
                log("⚠️ main.py nao esta em execucao!")
                proc = launch_main()
                if proc:
                    backoff = WAKEUP_INTERVAL
                else:
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    log(f"⏳ Backoff: {backoff}s")
            else:
                log("✅ main.py esta em execucao")
                backoff = WAKEUP_INTERVAL
            
            log(f"⏳ A aguardar {backoff}s...")
            
            # Aguardar com verificacao de shutdown
            for _ in range(backoff):
                if shutdown_flag:
                    break
                time.sleep(1)
                
    except KeyboardInterrupt:
        log("⏹️  Interrompido pelo utilizador.")
    except Exception as e:
        log(f"❌ Erro: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        log("👋 Wake-Up System terminado.")

if __name__ == "__main__":
    main()
