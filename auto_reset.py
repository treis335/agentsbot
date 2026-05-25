"""
Auto-Reset System v1.0
Reinicia automaticamente o Supervisor quando atinge limite de iteracoes
Volta ao trabalho em SEGUNDOS sem intervencao humana!
"""

import asyncio
import subprocess
import sys
import os
import time
import json
import threading
from datetime import datetime
from pathlib import Path

# Configuracoes
CHECK_INTERVAL = 3          # Verifica a cada 3 segundos
MAX_IDLE_SECONDS = 30       # 30 segundos sem atividade = reset
MAX_ITERATIONS = 8          # Maximo de iteracoes antes de reset
LOG_FILE = "auto_reset.log"

class AutoResetSystem:
    """
    Sistema que monitoriza o Supervisor e reinicia automaticamente
    quando atinge o limite de iteracoes ou fica inativo.
    Volta ao trabalho em SEGUNDOS!
    """
    
    def __init__(self):
        self.last_activity = datetime.now()
        self.reset_count = 0
        self.iteration_count = 0
        self.is_monitoring = False
        self._stop_event = threading.Event()
        self.memory_file = "memory/global/shared_memory.json"
        self.conversation_file = "memory/conversations/telegram_1094139387.json"
        
    def log(self, message):
        """Regista mensagem no log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def check_if_stuck(self):
        """Verifica se o Supervisor esta stuck"""
        
        # 1. Verifica ficheiros de log
        log_files = [
            "auto_recovery.log", "orchestrator.log", 
            "wakeup.log", "wakeup_v3.log", "main.log",
            "auto_reset.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for line in lines[-20:]:
                            if ("Limite de iteracoes" in line or 
                                "iteration limit" in line.lower()):
                                self.log(f"STUCK: {log_file} - {line.strip()}")
                                return True
                except:
                    pass
        
        # 2. Verifica tempo desde ultima atividade
        idle_seconds = (datetime.now() - self.last_activity).total_seconds()
        if idle_seconds > MAX_IDLE_SECONDS:
            self.log(f"STUCK: {int(idle_seconds)}s sem atividade (limite: {MAX_IDLE_SECONDS}s)")
            return True
        
        # 3. Verifica se ha processos Python a correr
        try:
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH',
                capture_output=True, text=True, shell=True, timeout=3
            )
            python_count = result.stdout.count("python.exe")
            if python_count == 0:
                self.log("STUCK: Nenhum processo Python ativo!")
                return True
        except:
            pass
        
        return False
    
    def force_reset(self):
        """Forca um reset completo do sistema"""
        self.reset_count += 1
        self.log(f"RESET #{self.reset_count} - A reiniciar sistema...")
        
        # 1. Mata todos os processos Python
        try:
            subprocess.run(
                'taskkill /F /FI "IMAGENAME eq python.exe" /T 2>nul',
                shell=True, timeout=5
            )
            self.log("Processos Python terminados")
        except:
            pass
        
        time.sleep(2)
        
        # 2. Limpa logs antigos (mantem apenas os ultimos 100)
        for log_file in ["auto_recovery.log", "orchestrator.log", 
                         "wakeup.log", "wakeup_v3.log", "auto_reset.log"]:
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if len(lines) > 100:
                        with open(log_file, "w", encoding="utf-8") as f:
                            f.writelines(lines[-50:])
                except:
                    pass
        
        # 3. Atualiza memoria global com timestamp do reset
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    memory = json.load(f)
                
                memory["last_reset"] = datetime.now().isoformat()
                memory["reset_count"] = self.reset_count
                memory["status"] = "auto_reset"
                
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    json.dump(memory, f, indent=2, ensure_ascii=False)
        except:
            pass
        
        # 4. Inicia o sistema principal
        scripts_to_try = [
            "main.py",
            "orchestrator_auto.py",
            "auto_evolve.py"
        ]
        
        for script in scripts_to_try:
            if os.path.exists(script):
                try:
                    subprocess.Popen(
                        [sys.executable, script],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                    self.log(f"Iniciado: {script}")
                    break
                except Exception as e:
                    self.log(f"Erro ao iniciar {script}: {e}")
        
        self.last_activity = datetime.now()
        self.log(f"RESET #{self.reset_count} concluido!")
    
    def monitor_loop(self):
        """Loop principal de monitorizacao"""
        self.log("=" * 60)
        self.log("Auto-Reset System v1.0")
        self.log(f"Verifica a cada: {CHECK_INTERVAL}s")
        self.log(f"Max idle: {MAX_IDLE_SECONDS}s")
        self.log(f"Auto-reset: ATIVO")
        self.log("=" * 60)
        
        while not self._stop_event.is_set():
            try:
                self.iteration_count += 1
                
                if self.check_if_stuck():
                    self.force_reset()
                    time.sleep(10)  # Espera o sistema arrancar
                else:
                    # Atualiza timestamp de atividade
                    self.last_activity = datetime.now()
                
                # Mostra status periodicamente
                if self.iteration_count % 20 == 0:
                    self.log(f"OK - {self.iteration_count} verificacoes, "
                            f"{self.reset_count} resets")
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                self.log("Interrompido pelo utilizador")
                break
            except Exception as e:
                self.log(f"Erro: {e}")
                time.sleep(CHECK_INTERVAL)
    
    def start(self):
        """Inicia a monitorizacao"""
        self.log("Iniciando Auto-Reset System...")
        thread = threading.Thread(target=self.monitor_loop, daemon=True)
        thread.start()
        self.is_monitoring = True
        self.log("Auto-Reset System ATIVO!")
        return thread
    
    def stop(self):
        """Para a monitorizacao"""
        self._stop_event.set()
        self.is_monitoring = False
        self.log("Auto-Reset System parado")


if __name__ == "__main__":
    reset = AutoResetSystem()
    
    print(f"\nAuto-Reset System v1.0")
    print(f"{'='*50}")
    print(f"Verifica a cada: {CHECK_INTERVAL} segundos")
    print(f"Max idle: {MAX_IDLE_SECONDS} segundos")
    print(f"Auto-reset: ATIVO")
    print(f"{'='*50}\n")
    
    thread = reset.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        reset.stop()
        print("\nAuto-Reset System parado.")
