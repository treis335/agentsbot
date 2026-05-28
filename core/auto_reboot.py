"""
core/auto_reboot.py - Sistema de auto-reboot imediato
Watchdog em thread separada que deteta o ficheiro de sinal em segundos.
"""

import os
import sys
import time
import threading
from pathlib import Path

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAG_FILE = os.path.join(PROJECT_DIR, "auto_reboot.flag")

def _watchdog():
    """Thread que vigia o ficheiro de reboot constantemente (a cada 1s)."""
    while True:
        if os.path.exists(FLAG_FILE):
            print("\n=== AUTO-REBOOT DETETADO PELO WATCHDOG ===")
            print("A REINICIAR SISTEMA IMEDIATAMENTE...\n")
            try:
                os.remove(FLAG_FILE)
            except:
                pass
            time.sleep(0.5)
            main_py = os.path.join(PROJECT_DIR, "main.py")
            os.execv(sys.executable, [sys.executable, main_py])
            break
        time.sleep(1)

def start_watchdog():
    """Inicia o watchdog numa thread separada (daemon)."""
    t = threading.Thread(target=_watchdog, daemon=True)
    t.start()
    print("[WATCHDOG] Ativo - a verificar auto_reboot.flag a cada 1s")

def trigger_reboot():
    """Dispara o reboot imediato criando o ficheiro de sinal."""
    try:
        Path(FLAG_FILE).write_text("reboot", encoding="utf-8")
        print("[REBOOT] Sinal enviado - watchdog vai detetar em segundos")
        return True
    except Exception as e:
        print(f"[REBOOT] Erro ao enviar sinal: {e}")
        return False

def check_and_reboot():
    """
    Verifica se o ficheiro de reboot existe e reinicia se sim.
    Usado como fallback no ciclo principal.
    """
    if os.path.exists(FLAG_FILE):
        print("\n=== AUTO-REBOOT DETETADO (FALLBACK) ===")
        try:
            os.remove(FLAG_FILE)
        except:
            pass
        time.sleep(0.5)
        main_py = os.path.join(PROJECT_DIR, "main.py")
        os.execv(sys.executable, [sys.executable, main_py])
        return True
    return False
