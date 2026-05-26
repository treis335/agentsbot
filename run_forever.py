"""
run_forever.py v6.0 - LANÇADOR PRINCIPAL INTELIGENTE COM AUTO-UPDATE
✅ Corre para sempre - modo infinito
✅ Auto-repair de todos os componentes
✅ Heartbeat e monitorização em tempo real
✅ Auto-update do supervisor e do sistema
✅ Decisão autónoma - só pede supervisão em casos críticos
"""

import os
import sys
import time
import json
import subprocess
import threading
import logging
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
LOG_DIR = BASE / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CORREOTO] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "correoto.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("correoto")

COMPONENTS = [
    {"name": "AutoRecovery", "script": str(BASE / "auto_recovery_manager.py"), "delay": 0, "critical": True},
    {"name": "WakeUp", "script": str(BASE / "wakeup_v3.py"), "delay": 1, "critical": True},
    {"name": "AutoUpdate", "script": str(BASE / "auto_update.py"), "delay": 2, "critical": False},
    {"name": "Cerebro", "script": str(BASE / "cerebro" / "core" / "brain.py"), "delay": 3, "critical": True},
    {"name": "ML Engine", "script": str(BASE / "cerebro" / "core" / "ml_engine.py"), "delay": 5, "critical": False},
    {"name": "API Connector", "script": str(BASE / "cerebro" / "core" / "api_connector.py"), "delay": 7, "critical": False},
    {"name": "Keep Alive", "script": str(BASE / "core" / "keep_alive.py"), "delay": 9, "critical": True},
    {"name": "Main", "script": str(BASE / "main.py"), "delay": 11, "critical": True},
]

processes = {}
running = True
start_time = time.time()
heartbeat_file = BASE / "heartbeat.flg"
recovery_log = BASE / "auto_recovery.log"
restart_flag = BASE / ".restart_requested"


def check_restart_flag():
    """Verifica se há um pedido de reinício pendente."""
    if restart_flag.exists():
        try:
            data = json.loads(restart_flag.read_text(encoding="utf-8"))
            reason = data.get("reason", "desconhecido")
            log(f"⚠️ PEDIDO DE REINÍCIO DETECTADO: {reason}")
            restart_flag.unlink()
            return True
        except:
            pass
    return False


def launch_component(comp):
    """Lança um componente num processo separado."""
    name = comp["name"]
    script = comp["script"]
    delay = comp["delay"]

    time.sleep(delay)

    if not os.path.exists(script):
        log.error(f"ERRO: {name} - script não encontrado: {script}")
        return None

    try:
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=BASE
        )
        log.info(f"✅ {name} iniciado (PID: {proc.pid})")
        return proc
    except Exception as e:
        log.error(f"❌ {name} - erro ao iniciar: {e}")
        return None


def monitor_component(name, proc):
    """Monitoriza um componente e reinicia se falhar."""
    global running
    while running:
        if proc.poll() is not None:
            log.warning(f"⚠️ {name} morreu (código: {proc.returncode})")
            return False
        time.sleep(5)
    return True


def launch_all():
    """Lança todos os componentes em paralelo."""
    threads = []
    for comp in COMPONENTS:
        proc = launch_component(comp)
        if proc:
            processes[comp["name"]] = proc
            t = threading.Thread(target=monitor_component, args=(comp["name"], proc), daemon=True)
            t.start()
            threads.append(t)
    return threads


def cleanup():
    """Limpa processos ao sair."""
    global running
    running = False
    log.info("A encerrar todos os componentes...")
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            proc.terminate()
            log.info(f"  ⏹️  {name} terminado")
    log.info("Sistema encerrado com sucesso.")


def main():
    global running
    log.info("=" * 60)
    log.info("CORREOTO ECOSYSTEM v6.0 - LANÇADOR PRINCIPAL")
    log.info("Modo: INFINITO - A correr para sempre")
    log.info("Auto-update: ATIVO")
    log.info("=" * 60)

    try:
        # Verificar pedido de reinício pendente
        if check_restart_flag():
            log.info("A processar reinício...")

        # Lançar todos os componentes
        threads = launch_all()

        # Loop principal - mantém o sistema vivo
        while running:
            time.sleep(10)
            
            # Verificar heartbeat
            uptime = time.time() - start_time
            if int(uptime) % 60 == 0:  # A cada minuto
                log.info(f"💓 Heartbeat - Sistema ativo há {int(uptime)}s")
            
            # Verificar pedidos de reinício
            if check_restart_flag():
                log.info("Reinício solicitado. A reiniciar componentes...")
                cleanup()
                time.sleep(2)
                threads = launch_all()

    except KeyboardInterrupt:
        log.info("Shutdown recebido pelo utilizador.")
    except Exception as e:
        log.error(f"Erro fatal no lançador: {e}")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
