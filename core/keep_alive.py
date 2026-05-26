"""
keep_alive.py - MANTEM O ECOSSISTEMA CORREOTO VIVO 24/7
Corre em loop infinito, monitoriza e reinicia tudo automaticamente.
"""
import os, sys, time, json, subprocess, threading, logging
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
LOG = BASE / "core" / "keep_alive.log"
HEARTBEAT = BASE / "core" / "heartbeat.json"
PID_FILE = BASE / "core" / "keep_alive.pid"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [KEEP_ALIVE] %(message)s",
    handlers=[
        logging.FileHandler(LOG, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("keep_alive")

COMPONENTS = {
    "brain": {
        "script": str(BASE / "cerebro" / "core" / "brain.py"),
        "args": [],
        "check": lambda: (BASE / "cerebro" / "core" / "brain.py").exists()
    },
    "ml_engine": {
        "script": str(BASE / "cerebro" / "core" / "ml_engine.py"),
        "args": [],
        "check": lambda: (BASE / "cerebro" / "core" / "ml_engine.py").exists()
    },
    "api_connector": {
        "script": str(BASE / "cerebro" / "core" / "api_connector.py"),
        "args": [],
        "check": lambda: (BASE / "cerebro" / "core" / "api_connector.py").exists()
    }
}

processes = {}
start_time = time.time()

def write_heartbeat(status):
    """Escreve heartbeat com estado atual."""
    hb = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "processes": {k: "RUNNING" if v and v.poll() is None else "STOPPED" for k, v in processes.items()},
        "uptime": time.time() - start_time
    }
    with open(HEARTBEAT, "w") as f:
        json.dump(hb, f, indent=2)

def start_component(name, info):
    """Inicia um componente como subprocesso."""
    script = info["script"]
    if not os.path.exists(script):
        log.warning("ATENCAO: " + name + " - script nao encontrado: " + script)
        return None
    
    try:
        proc = subprocess.Popen(
            [sys.executable, script] + info["args"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        log.info(name + " iniciado (PID: " + str(proc.pid) + ")")
        return proc
    except Exception as e:
        log.error("ERRO ao iniciar " + name + ": " + str(e))
        return None

def check_and_restart():
    """Verifica todos os componentes e reinicia se necessario."""
    for name, info in COMPONENTS.items():
        proc = processes.get(name)
        
        if proc is None or proc.poll() is not None:
            if proc is not None:
                log.warning("ATENCAO: " + name + " parou (codigo: " + str(proc.returncode) + "). A reiniciar...")
            else:
                log.info("A iniciar " + name + "...")
            
            new_proc = start_component(name, info)
            if new_proc:
                processes[name] = new_proc
    
    write_heartbeat("RUNNING")

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("KEEP ALIVE A INICIAR...")
    log.info("=" * 50)
    
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    try:
        while True:
            check_and_restart()
            time.sleep(15)
    except KeyboardInterrupt:
        log.info("Keep Alive interrompido")
    except Exception as e:
        log.error("Erro no Keep Alive: " + str(e))
        time.sleep(5)
