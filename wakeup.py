"""
Wake-Up System v2.0 - Acorda em SEGUNDOS quando atinge limite de iteracoes
Monitoriza constantemente e reinicia automaticamente
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
WAKEUP_INTERVAL_FAST = 5       # 5 segundos para detecao rapida
WAKEUP_INTERVAL_NORMAL = 60    # 60 segundos para monitorizacao normal
MAX_ITERATIONS = 10
LOG_FILE = "wakeup.log"

class WakeUpSystemV2:
    """
    Sistema melhorado que deteta "Limite de iteracoes" em SEGUNDOS
    e reinicia automaticamente sem esperar 1 minuto.
    """
    
    def __init__(self):
        self.iteration_count = 0
        self.last_wakeup = datetime.now()
        self.is_monitoring = False
        self.wakeup_history = []
        self.stuck_detected = False
        self._stop_event = threading.Event()
        
    def log(self, message):
        """Regista mensagem no log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def detect_stuck_fast(self):
        """Deteccao RAPIDA de stuck - verifica a cada 5 segundos"""
        # 1. Verifica ficheiros de log por "Limite de iteracoes"
        log_files = ["auto_recovery.log", "orchestrator.log", "wakeup.log", "main.log"]
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        # Verifica as ultimas 20 linhas
                        for line in lines[-20:]:
                            if "Limite de iteracoes" in line or "iteration limit" in line.lower():
                                self.log(f"[!] DETETADO: Limite de iteracoes em {log_file}!")
                                return True
                except:
                    pass
        
        # 2. Verifica se o processo python principal (main.py) ainda existe
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python3.13.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=3
            )
            python_count = result.stdout.count("python3.13.exe")
            # Só considera stuck se houver 0 ou 1 processos (apenas o wakeup)
            if python_count <= 1:
                self.log("[!] Apenas wakeup.py ativo - main.py pode ter morrido!")
                return True
            # Se houver mais de 3 processos python, há duplicatas - não reiniciar
            if python_count > 3:
                self.log(f"[!] {python_count} processos detetados - possivel duplicacao. A aguardar...")
                return False
        except:
            pass
        
        # 3. Verifica timestamp do ultimo log - se > 30s sem atividade, esta preso
        if os.path.exists(LOG_FILE):
            try:
                mod_time = os.path.getmtime(LOG_FILE)
                elapsed = time.time() - mod_time
                if elapsed > 120:  # Mais de 2min sem logs (aumentado de 30s para evitar falsos stuck)
                    self.log(f"[!] Sem atividade ha {elapsed:.0f}s - a verificar...")
                    return True
            except:
                pass
        
        return False
    
    def force_restart(self):
        """Forca o reinicio do sistema principal com rate limiting"""
        # Rate limiting: max 3 reinícios por minuto
        now = time.time()
        if now - self.last_restart_time < 60:
            self.restart_count += 1
            if self.restart_count > self.max_restarts_per_minute:
                cooldown = 120  # 2 minutos de espera
                self.log(f"[BACKOFF] Demasiados reinicios ({self.restart_count}/min). A aguardar {cooldown}s...")
                time.sleep(cooldown)
                self.restart_count = 0
        else:
            self.restart_count = 1
        self.last_restart_time = now
        
        self.log("[LANCAR] A FORCAR REINICIO DO SISTEMA...")
        
        # Mata processos python antigos (exceto este)
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python3.13.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=3
            )
            
            current_pid = os.getpid()
            for line in result.stdout.split("\n"):
                if "python3.13.exe" in line and str(current_pid) not in line:
                    # Extrai PID
                    parts = line.split(",")
                    if len(parts) >= 2:
                        pid = parts[1].strip().strip('"')
                        if pid.isdigit() and int(pid) != current_pid:
                            try:
                                os.kill(int(pid), 9)
                                self.log(f"[FATAL] Processo {pid} morto")
                            except:
                                pass
        except:
            pass
        
        # Inicia o sistema principal novamente
        main_scripts = ["main.py", "orchestrator_auto.py", "auto_evolve.py"]
        for script in main_scripts:
            if os.path.exists(script):
                try:
                    subprocess.Popen(
                        [sys.executable, script],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                    self.log(f"[OK] {script} reiniciado!")
                    break
                except Exception as e:
                    self.log(f"[X] Erro ao reiniciar {script}: {e}")
        
        self.stuck_detected = False
        self.iteration_count = 0
    
    def monitor_loop_fast(self):
        """Loop de monitorizacao RAPIDA (5 segundos)"""
        self.log("[BUSCA] Iniciando monitorizacao RAPIDA (5s)...")
        
        while not self._stop_event.is_set():
            try:
                if self.detect_stuck_fast():
                    self.stuck_detected = True
                    self.log("[!] SISTEMA PRESO DETETADO! A reiniciar em 5 segundos...")
                    time.sleep(5)
                    self.force_restart()
                else:
                    if self.stuck_detected:
                        self.log("[OK] Sistema recuperado!")
                        self.stuck_detected = False
                
                # Espera 5 segundos antes de verificar novamente
                self._stop_event.wait(timeout=WAKEUP_INTERVAL_FAST)
                
            except Exception as e:
                self.log(f"[X] Erro no monitor loop: {e}")
                time.sleep(WAKEUP_INTERVAL_FAST)
    
    def start_monitoring(self):
        """Inicia a monitorizacao em thread separada"""
        self.log("[LANCAR] WakeUpSystemV2 iniciado!")
        self.log(f"[ALARM] Intervalo rapido: {WAKEUP_INTERVAL_FAST}s")
        self.log(f"[ALARM] Intervalo normal: {WAKEUP_INTERVAL_NORMAL}s")
        
        # Thread para monitorizacao rapida
        monitor_thread = threading.Thread(target=self.monitor_loop_fast, daemon=True)
        monitor_thread.start()
        
        # Thread para monitorizacao normal (backup)
        normal_thread = threading.Thread(target=self.monitor_loop_normal, daemon=True)
        normal_thread.start()
        
        self.log("[OK] Monitorizacao ativa!")
        
        # Mantem o programa a correr
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("[PARAR] WakeUpSystem parado pelo utilizador")
            self._stop_event.set()
    
    def monitor_loop_normal(self):
        """Loop de monitorizacao normal (60 segundos) - backup"""
        while not self._stop_event.is_set():
            try:
                if not self.stuck_detected:  # So verifica se o rapido nao detetou
                    if self.detect_stuck_fast():
                        self.stuck_detected = True
                        self.log("[!] (Backup) SISTEMA PRESO DETETADO!")
                        self.force_restart()
                
                self._stop_event.wait(timeout=WAKEUP_INTERVAL_NORMAL)
            except:
                pass


# ====================== MAIN ======================
if __name__ == "__main__":
    print("=" * 60)
    print("  WakeUp System v2.0 - Detecao Rapida de Stuck")
    print("  Monitoriza a cada 5 segundos!")
    print("=" * 60)
    
    system = WakeUpSystemV2()
    system.start_monitoring()
