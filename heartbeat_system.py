"""
Heartbeat System v3.1 - ULTRA RESILIENTE (com fix encoding)
Sistema que bate o heartbeat continuamente mesmo quando o Supervisor atinge limite.
Usa um processo separado que NUNCA para.
"""

import os
import time
import json
import sys
import subprocess
from datetime import datetime

# Fix encoding para Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HEARTBEAT_FILE = "heartbeat.flg"
STOP_SIGNAL_FILE = "STOP_SIGNAL.flg"
MEMORY_FILE = "memory/global/shared_memory.json"
LOG_FILE = "heartbeat_system.log"
CHECK_INTERVAL = 2  # segundos

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}"
    print(entry, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
        f.write(entry + "\n")

def check_if_supervisor_stuck():
    """Verifica se o Supervisor esta stuck (atingiu limite de iteracoes)"""
    try:
        # Metodo 1: Verificar ficheiro de memoria (com encoding fix)
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            
            # Se contem "limite de iteracoes" ou similar
            stuck_indicators = [
                "limite de itera", "iteration limit", 
                "atingido", "stuck", "parado"
            ]
            
            for indicator in stuck_indicators:
                if indicator.lower() in content.lower():
                    log(f" Supervisor STUCK detectado! (indicador: {indicator})")
                    return True
        
        # Metodo 2: Verificar se o heartbeat foi atualizado recentemente
        if os.path.exists(HEARTBEAT_FILE):
            mod_time = os.path.getmtime(HEARTBEAT_FILE)
            elapsed = time.time() - mod_time
            if elapsed > 30:  # Mais de 30s sem heartbeat
                log(f" Heartbeat parado ha {elapsed:.0f}s! Supervisor STUCK!")
                return True
        
        # Metodo 3: Verificar logs do auto_reset
        if os.path.exists("auto_reset_v2.log"):
            with open("auto_reset_v2.log", "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    if "limite" in line.lower() and "itera" in line.lower():
                        log(f" Limite de iteracoes detectado no log!")
                        return True
        
        return False
    
    except Exception as e:
        log(f"Erro ao verificar stuck: {e}")
        return False

def restart_supervisor():
    """Reinicia o Supervisor e sistemas auxiliares"""
    log(" A reiniciar Supervisor...")
    
    try:
        # Mata processos python existentes
        if os.name == 'nt':  # Windows
            subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                         capture_output=True, timeout=5)
        else:  # Linux/Mac
            subprocess.run(["pkill", "-f", "python"], 
                         capture_output=True, timeout=5)
        
        time.sleep(2)
        
        # Inicia novamente
        subprocess.Popen(["python", "auto_reset_v2.py"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        subprocess.Popen(["python", "main.py"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        log(" Supervisor reiniciado com sucesso!")
        
        # Cria sinal para o keep_alive.bat
        with open(STOP_SIGNAL_FILE, "w") as f:
            f.write(f"Reiniciado em {datetime.now()}")
        
        return True
    
    except Exception as e:
        log(f"Erro ao reiniciar: {e}")
        return False

def update_heartbeat():
    """Atualiza o heartbeat"""
    try:
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        log(f"Erro ao atualizar heartbeat: {e}")

def main():
    log("=" * 60)
    log("HEARTBEAT SYSTEM v3.1 INICIADO")
    log("=" * 60)
    log(f"Check interval: {CHECK_INTERVAL}s")
    log("A monitorizar Supervisor 24/7...")
    log("=" * 60)
    
    consecutive_stuck = 0
    max_consecutive_stuck = 3  # So reinicia apos 3 detecoes consecutivas
    
    while True:
        try:
            # 1. Atualiza heartbeat (sempre!)
            update_heartbeat()
            
            # 2. Verifica se Supervisor esta stuck
            stuck = check_if_supervisor_stuck()
            
            if stuck:
                consecutive_stuck += 1
                log(f" Stuck detection #{consecutive_stuck}/{max_consecutive_stuck}")
                
                if consecutive_stuck >= max_consecutive_stuck:
                    log(" MULTIPLAS DETECOES! A reiniciar Supervisor...")
                    restart_supervisor()
                    consecutive_stuck = 0
                    time.sleep(5)  # Espera o restart
            else:
                if consecutive_stuck > 0:
                    log(" Supervisor recuperou! A diminuir contagem...")
                    consecutive_stuck = max(0, consecutive_stuck - 1)
            
            # 3. Espera
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("Heartbeat System interrompido pelo utilizador")
            break
        except Exception as e:
            log(f"Erro no loop principal: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
