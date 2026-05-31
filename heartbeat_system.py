"""
Heartbeat System v5.1 - CORRIGIDO
==================================
Sistema que monitoriza o ecossistema Correoto e reinicia se necessário.
v5.1: Corrige UnicodeEncodeError, remove ref a supervisor_ultra.py (inexistente),
      adiciona timeouts seguros, usa logging em vez de print.
"""

import os
import time
import json
import sys
import subprocess
import logging
from datetime import datetime

# ─── Logging robusto (à prova de UnicodeEncodeError) ──────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("heartbeat_system.log", encoding="utf-8", mode="a"),
    ]
)
logger = logging.getLogger("heartbeat")

# Forçar UTF-8 no stdout (previne UnicodeEncodeError com emojis no Windows)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Configuração ──────────────────────────────────────────────────────────────
HEARTBEAT_FILE = "heartbeat.flg"
STOP_SIGNAL_FILE = "STOP_SIGNAL.flg"
MEMORY_FILE = "memory/global/shared_memory.json"
SMART_PACE_FILE = "smart_pace.flg"
DEEP_WORK_FILE = "deep_work.flg"
CHECK_INTERVAL = 5  # segundos (era 2 — reduzimos polling)
MAX_IDLE_SECONDS = 60  # segundos (era 30 — mais tolerante)
MIN_RESTART_INTERVAL = 30  # segundos mínimo entre reinícios


def log(msg):
    """Log seguro — substitui emojis/problem chars por '?' se necessário."""
    logger.info(msg)


def update_heartbeat():
    """Atualiza o ficheiro de heartbeat."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "unix_time": time.time(),
        "status": "alive",
        "pid": os.getpid(),
        "mode": "stable",
    }
    try:
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        log(f"[WARN] Erro ao atualizar heartbeat: {e}")


def check_if_supervisor_stuck():
    """Verifica se o Supervisor está preso."""
    try:
        # Método 1: Verificar ficheiro de memória
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            content = json.dumps(data)
            if "limite de itera" in content.lower() or "iteration limit" in content.lower():
                log("[!] Limite de iteracoes detectado na memoria!")
                return True

        # Método 2: Verificar heartbeat
        if os.path.exists(HEARTBEAT_FILE):
            with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                hb = json.load(f)
            hb_time = datetime.fromisoformat(hb["timestamp"])
            diff = (datetime.now() - hb_time).total_seconds()
            if diff > MAX_IDLE_SECONDS:
                log(f"[!] Heartbeat parado ha {diff:.0f}s!")
                return True

        # Método 3: Verificar processos Python
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "main.py" not in result.stdout:
                log("[!] Nenhum processo main.py do Correoto encontrado!")
                return True
        except subprocess.TimeoutExpired:
            log("[WARN] tasklist timeout (nao critico)")
        except Exception:
            pass

        return False

    except Exception as e:
        log(f"[X] Erro ao verificar stuck: {e}")
        return False


def restart_supervisor():
    """Reinicia o main.py (supervisor principal) de forma segura."""
    log("[LOOP] A reiniciar o ecossistema Correoto (main.py)...")

    # Mata processos Python antigos (exceto este)
    try:
        subprocess.run(
            ["taskkill", "/F", "/FI", "WINDOWTITLE eq main*"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass

    # Inicia main.py diretamente (sem supervisor_ultra.py que já não existe)
    try:
        subprocess.Popen(
            [sys.executable, "main.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        log("[OK] main.py reiniciado com sucesso!")
    except Exception as e:
        log(f"[X] Erro ao reiniciar main.py: {e}")


def main():
    """Loop principal do Heartbeat System."""
    log("=" * 60)
    log("HEARTBEAT SYSTEM v5.1 - ESTAVEL")
    log("Monitorizando ecossistema Correoto...")
    log("=" * 60)

    restart_count = 0
    last_restart_time = 0

    while True:
        try:
            update_heartbeat()

            if check_if_supervisor_stuck():
                current_time = time.time()
                if current_time - last_restart_time > MIN_RESTART_INTERVAL:
                    restart_count += 1
                    log(f"[LOOP] Restart #{restart_count}")
                    restart_supervisor()
                    last_restart_time = current_time
                else:
                    log("[TIME] A aguardar antes de reiniciar (cooldown)...")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            log("[PARAR] Heartbeat System parado pelo utilizador")
            break
        except Exception as e:
            log(f"[X] Erro no loop principal: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
