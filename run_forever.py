"""
run_forever.py v3.0 - LANCADOR PRINCIPAL DO ECOSSISTEMA CORREOTO
Inicia todos os componentes em paralelo e mantem tudo vivo.
CORRE PARA SEMPRE - nunca para a menos que o utilizador pare.
Sem limites de iteracoes - verdadeiro modo infinito.
"""
import os, sys, time, json, subprocess, threading, logging
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
    {
        "name": "AutoRecovery",
        "script": str(BASE / "auto_recovery_manager.py"),
        "delay": 0,
        "critical": True
    },
    {
        "name": "WakeUp",
        "script": str(BASE / "wakeup_v3.py"),
        "delay": 1,
        "critical": True
    },
    {
        "name": "Cerebro",
        "script": str(BASE / "cerebro" / "core" / "brain.py"),
        "delay": 2,
        "critical": True
    },
    {
        "name": "ML Engine",
        "script": str(BASE / "cerebro" / "core" / "ml_engine.py"),
        "delay": 4,
        "critical": False
    },
    {
        "name": "API Connector",
        "script": str(BASE / "cerebro" / "core" / "api_connector.py"),
        "delay": 6,
        "critical": False
    },
    {
        "name": "Keep Alive",
        "script": str(BASE / "core" / "keep_alive.py"),
        "delay": 8,
        "critical": True
    }
]

processes = {}
running = True
start_time = time.time()

def launch_component(comp):
    """Lanca um componente num processo separado."""
    name = comp["name"]
    script = comp["script"]
    delay = comp["delay"]
    
    time.sleep(delay)
    
    if not os.path.exists(script):
        log.error(f"❌ ERRO: {name} - script nao encontrado: {script}")
        return None
    
    log.info(f"🚀 A lancar {name}...")
    
    try:
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        processes[name] = proc
        log.info(f"✅ {name} lancado (PID: {proc.pid})")
        return proc
    except Exception as e:
        log.error(f"❌ ERRO ao lancar {name}: {e}")
        return None

def monitor_components():
    """Monitoriza componentes em background e reinicia se necessário."""
    global running
    
    log.info("🔍 Monitor de componentes iniciado")
    
    while running:
        time.sleep(10)
        
        for name, proc in list(processes.items()):
            if proc is None:
                continue
            
            # Verifica se o processo ainda está vivo
            if proc.poll() is not None:
                log.warning(f"⚠️ {name} parou (código: {proc.returncode})")
                
                # Tenta reiniciar
                comp = next((c for c in COMPONENTS if c["name"] == name), None)
                if comp:
                    log.info(f"🔄 A reiniciar {name}...")
                    new_proc = launch_component(comp)
                    if new_proc:
                        processes[name] = new_proc
                        log.info(f"✅ {name} reiniciado com sucesso!")
                    else:
                        log.error(f"❌ Falha ao reiniciar {name}")
                        if comp.get("critical", False):
                            log.critical(f"💀 Componente critico {name} nao recuperou!")
        
        # Log de saúde periódico
        uptime = time.time() - start_time
        alive = sum(1 for p in processes.values() if p and p.poll() is None)
        log.info(f"💚 [SAUDE] {alive}/{len(COMPONENTS)} componentes vivos | Uptime: {uptime:.0f}s")

def main():
    """Funcao principal - corre para sempre"""
    global running
    
    log.info("=" * 60)
    log.info("🚀 CORREOTO ECOSYSTEM v3.0 - MODO INFINITO")
    log.info("📅 " + datetime.now().isoformat())
    log.info("=" * 60)
    
    # Inicia monitor em background
    monitor_thread = threading.Thread(target=monitor_components, daemon=True)
    monitor_thread.start()
    
    # Lança todos os componentes
    for comp in COMPONENTS:
        launch_component(comp)
    
    log.info("✅ Todos os componentes lancados!")
    log.info(f"📊 Total: {len(COMPONENTS)} componentes")
    
    # Loop principal - corre para sempre
    try:
        while running:
            time.sleep(30)
            
            # Mostra estado periódico
            alive = sum(1 for p in processes.values() if p and p.poll() is None)
            uptime = time.time() - start_time
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            
            log.info(f"💚 [HEARTBEAT] {alive}/{len(COMPONENTS)} vivos | Uptime: {hours}h{minutes}m")
            
    except KeyboardInterrupt:
        log.info("🛑 CORREOTO interrompido pelo utilizador")
        running = False
        
        # Termina processos filhos
        for name, proc in processes.items():
            if proc and proc.poll() is None:
                log.info(f"🛑 A terminar {name}...")
                proc.terminate()
        
        log.info("👋 CORREOTO encerrado. Até breve!")

if __name__ == "__main__":
    main()
