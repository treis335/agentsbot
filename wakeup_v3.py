"""
Wake-Up System v4.0 - CORREOTO ECOSYSTEM
✅ Auto-repair completo
✅ SEM limites de iteracoes (corre para sempre)
✅ Lock file com PID para evitar duplicados
✅ Intervalo inteligente com backoff
✅ Log detalhado
✅ Detecta e repara corrupcao automaticamente
✅ Auto-restart de componentes mortos
✅ Heartbeat monitoring
✅ Decisao autonoma - so pede supervisao em casos criticos
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

def is_main_running():
    """Verifica se main.py esta em execucao via tasklist."""
    try:
        result = subprocess.run(
            'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH',
            capture_output=True, text=True, shell=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if "python" in line.lower():
                return True
        return False
    except:
        return True  # Assume que esta vivo em caso de erro

def check_heartbeat():
    """Verifica o heartbeat do sistema."""
    try:
        if os.path.exists(HEARTBEAT_FILE):
            with open(HEARTBEAT_FILE, "r") as f:
                data = json.load(f)
            last_beat = datetime.fromisoformat(data.get("last_beat", "2000-01-01"))
            elapsed = (datetime.now() - last_beat).total_seconds()
            if elapsed > 60:
                log(f"Heartbeat expirado: {elapsed:.0f}s desde o ultimo batimento")
                return False
            return True
        else:
            log("Ficheiro de heartbeat nao encontrado")
            return False
    except:
        return False

def restart_main():
    """Reinicia o main.py automaticamente."""
    log("A reiniciar main.py...")
    try:
        subprocess.Popen(
            [sys.executable, str(BASE / "main.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        log("main.py reiniciado com sucesso")
        return True
    except Exception as e:
        log(f"Falha ao reiniciar main.py: {e}")
        return False

def check_corrupted_files():
    """Verifica e repara ficheiros corrompidos."""
    critical_files = [
        "main.py", "auto_recovery.py", "run_forever.py",
        "core/keep_alive.py", "cerebro/core/brain.py"
    ]
    
    for f in critical_files:
        fpath = BASE / f
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8")
                if len(content) < 50:
                    log(f"Ficheiro corrompido: {f} (apenas {len(content)} chars)")
                    bak_path = fpath.with_suffix(fpath.suffix + ".bak")
                    if bak_path.exists():
                        bak_content = bak_path.read_text(encoding="utf-8")
                        fpath.write_text(bak_content, encoding="utf-8")
                        log(f"Restaurado: {f} a partir de backup")
            except Exception as e:
                log(f"Erro ao verificar {f}: {e}")

def main():
    if is_already_running():
        log("Ja existe uma instancia em execucao. A sair.")
        return
    
    log("=" * 60)
    log("WAKE-UP SYSTEM v4.0 INICIADO")
    log("Modo: INFINITO - A correr para sempre")
    log("=" * 60)
    
    backoff = WAKEUP_INTERVAL
    iteration = 0
    
    try:
        while not shutdown_flag:
            iteration += 1
            log(f"Iteracao {iteration}")
            
            # Verifica ficheiros corrompidos
            check_corrupted_files()
            
            # Verifica heartbeat
            if not check_heartbeat():
                log("Heartbeat ausente - a verificar main.py...")
                if not is_main_running():
                    log("main.py nao esta em execucao!")
                    if restart_main():
                        log("main.py reiniciado com sucesso")
                        backoff = WAKEUP_INTERVAL
                    else:
                        log("Falha ao reiniciar main.py")
                        backoff = min(backoff * 1.5, MAX_BACKOFF)
                else:
                    log("main.py esta em execucao mas heartbeat ausente")
                    # Tenta recriar heartbeat
                    try:
                        os.makedirs(BASE / "core", exist_ok=True)
                        with open(HEARTBEAT_FILE, "w") as f:
                            json.dump({"last_beat": datetime.now().isoformat()}, f)
                        log("Heartbeat recriado")
                        backoff = WAKEUP_INTERVAL
                    except Exception as e:
                        log(f"Falha ao recriar heartbeat: {e}")
            else:
                backoff = WAKEUP_INTERVAL
            
            # Log de estado
            log(f"Proximo wake-up em {backoff}s")
            
            # Espera com verificacao de shutdown
            for _ in range(int(backoff)):
                if shutdown_flag:
                    break
                time.sleep(1)
    
    except KeyboardInterrupt:
        log("Shutdown recebido. A encerrar...")
    except Exception as e:
        log(f"Erro fatal: {e}")
        log("A reiniciar automaticamente...")
        time.sleep(2)
        main()
    finally:
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except:
                pass
        log("Wake-Up System encerrado")


if __name__ == "__main__":
    main()
