"""
run_forever.py v7.0 - LANÇADOR PRINCIPAL INTELIGENTE COM AUTO-UPDATE
[OK] Corre para sempre - modo infinito
[OK] Auto-repair de todos os componentes
[OK] Heartbeat e monitorização em tempo real
[OK] Auto-update do supervisor e do sistema
[OK] Decisão autónoma - só pede supervisão em casos críticos
[OK] Verificação de integridade de ficheiros
[OK] Ciclo de auto-evolução contínuo
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

# Ficheiros críticos para verificação de integridade
FICHEIROS_CRITICOS = [
    "agents/souls/supervisor.md",
    "auto_update.py",
    "run_forever.py",
    "auto_recovery.py",
    "auto_recovery_manager.py",
    "wakeup_v3.py",
    "main.py",
]

def check_restart_flag():
    """Verifica se há um pedido de reinício pendente."""
    if restart_flag.exists():
        try:
            content = restart_flag.read_text(encoding="utf-8").strip()
            if content == "restart_requested":
                log("[LOOP] Pedido de reinício detetado!")
                restart_flag.unlink(missing_ok=True)
                return True
        except:
            pass
    return False

def verify_integrity():
    """Verifica integridade dos ficheiros críticos."""
    issues = []
    for ficheiro in FICHEIROS_CRITICOS:
        path = BASE / ficheiro
        if not path.exists():
            issues.append(f"[X] {ficheiro} - NÃO EXISTE")
        elif path.stat().st_size < 100:
            issues.append(f"[!] {ficheiro} - Tamanho suspeito: {path.stat().st_size} bytes")
    return issues

def launch_component(component):
    """Lança um componente em processo separado."""
    name = component["name"]
    script = component["script"]
    delay = component["delay"]
    
    time.sleep(delay)
    
    while running:
        try:
            log(f"[START] A lançar {name}...")
            proc = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=BASE
            )
            processes[name] = proc
            log(f"[OK] {name} lançado (PID: {proc.pid})")
            
            # Aguarda o processo terminar
            stdout, stderr = proc.communicate()
            
            if proc.returncode != 0:
                log(f"[!] {name} terminou com código {proc.returncode}")
                if stderr:
                    log(f"   Erro: {stderr[-500:]}")
            
            # Se for crítico, reinicia imediatamente
            if component["critical"]:
                log(f"[LOOP] A reiniciar {name} (componente crítico)...")
                time.sleep(1)
            else:
                log(f"[PAUSE] {name} não é crítico, a aguardar...")
                time.sleep(10)
                
        except Exception as e:
            log(f"[X] Erro ao lançar {name}: {e}")
            time.sleep(5)

def update_heartbeat():
    """Atualiza o heartbeat periodicamente."""
    while running:
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time() - start_time,
                "processes": {k: v.pid if v else None for k, v in processes.items()},
                "status": "running"
            }
            heartbeat_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except:
            pass
        time.sleep(30)

def auto_evolve_cycle():
    """Ciclo de auto-evolução - verifica e melhora o sistema."""
    cycles = 0
    while running:
        cycles += 1
        log(f"[LOOP] Ciclo de auto-evolução #{cycles}")
        
        # Verificar integridade
        issues = verify_integrity()
        if issues:
            log("[!] Problemas de integridade detetados:")
            for issue in issues:
                log(f"   {issue}")
        
        # Verificar restart flag
        if check_restart_flag():
            log("[LOOP] A preparar reinício do sistema...")
            time.sleep(2)
            # O reinício será tratado pelo supervisor
        
        # Heartbeat update
        update_heartbeat()
        
        # Aguardar 5 minutos entre ciclos
        log("[TIME] A aguardar 5 min até próximo ciclo...")
        time.sleep(300)

def main():
    log("=" * 60)
    log("[START] CORREOTO ECOSYSTEM v7.0 - INICIADO")
    log(f"[PASTA] Diretório: {BASE}")
    log(f"[ALARM] Início: {datetime.now().isoformat()}")
    log("=" * 60)
    
    # Verificar integridade inicial
    log("\n[BUSCA] A verificar integridade dos ficheiros...")
    issues = verify_integrity()
    if issues:
        log("[!] Problemas detetados:")
        for issue in issues:
            log(f"   {issue}")
    else:
        log("[OK] Todos os ficheiros OK!")
    
    # Lançar componentes em threads
    threads = []
    for component in COMPONENTS:
        t = threading.Thread(target=launch_component, args=(component,), daemon=True)
        t.start()
        threads.append(t)
        log(f"[LISTA] {component['name']} agendado (delay: {component['delay']}s)")
    
    # Ciclo de auto-evolução
    log("\n[LOOP] A iniciar ciclo de auto-evolução...")
    auto_evolve_cycle()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n[STOP]  Sistema interrompido pelo utilizador.")
        running = False
    except Exception as e:
        log(f"\n[X] Erro fatal: {e}")
        running = False
    finally:
        log("[TCHAU] Sistema terminado.")
