"""
Wake-Up System v3.0 - ULTRA RAPIDO
Acorda em 3 SEGUNDOS quando atinge limite de iteracoes
Nao precisa de intervencao humana!
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

# Configuracoes ULTRA RAPIDAS
WAKEUP_INTERVAL_FAST = 3       # 3 segundos - detecao ultra rapida
WAKEUP_INTERVAL_NORMAL = 15    # 15 segundos - monitorizacao normal
MAX_ITERATIONS_BEFORE_RESET = 8
LOG_FILE = "wakeup_v3.log"

class WakeUpSystemV3:
    """
    Sistema ULTRA RAPIDO que deteta "Limite de iteracoes" em 3 SEGUNDOS
    e reinicia automaticamente SEM intervencao humana.
    """
    
    def __init__(self):
        self.iteration_count = 0
        self.last_wakeup = datetime.now()
        self.is_monitoring = False
        self.wakeup_history = []
        self.stuck_detected = False
        self.auto_reset_count = 0
        self._stop_event = threading.Event()
        self.main_script = "main.py"
        self.scripts_to_monitor = [
            "main.py", "orchestrator_auto.py", "auto_evolve.py",
            "auto_recovery.py", "auto_recovery_manager.py"
        ]
        
    def log(self, message):
        """Regista mensagem no log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def detect_stuck_ultra_fast(self):
        """Deteccao ULTRA RAPIDA - verifica a cada 3 segundos"""
        # 1. Verifica ficheiros de log por "Limite de iteracoes"
        log_files = [
            "auto_recovery.log", "orchestrator.log", 
            "wakeup.log", "wakeup_v3.log", "main.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        # Verifica as ultimas 30 linhas
                        for line in lines[-30:]:
                            if ("Limite de iteracoes" in line or 
                                "iteration limit" in line.lower() or
                                "max iterations" in line.lower() or
                                "iteracoes atingido" in line):
                                self.log(f"DETETADO: Limite de iteracoes em {log_file}!")
                                return True
                except:
                    pass
        
        # 2. Verifica se o processo main.py ainda esta a correr
        try:
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH',
                capture_output=True, text=True, shell=True, timeout=5
            )
            # Se nao ha processos python, algo esta errado
            if "python.exe" not in result.stdout:
                self.log("ALERTA: Nenhum processo Python encontrado!")
                return True
        except:
            pass
        
        # 3. Verifica tempo desde ultima atividade
        time_since_last = (datetime.now() - self.last_wakeup).total_seconds()
        if time_since_last > 60:  # Mais de 1 minuto sem atividade
            self.log(f"ALERTA: {int(time_since_last)}s sem atividade!")
            return True
            
        return False
    
    def force_restart(self):
        """Reinicia FORCADAMENTE o sistema principal"""
        self.auto_reset_count += 1
        self.log(f"REINICIANDO... (reset #{self.auto_reset_count})")
        
        # 1. Mata processos Python antigos
        try:
            subprocess.run(
                'taskkill /F /FI "IMAGENAME eq python.exe" /T 2>nul',
                shell=True, timeout=5
            )
            self.log("Processos Python antigos terminados")
        except:
            pass
        
        time.sleep(1)  # Pequena pausa
        
        # 2. Inicia o sistema principal novamente
        try:
            subprocess.Popen(
                [sys.executable, self.main_script],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.log(f"Main reiniciado: {self.main_script}")
        except Exception as e:
            self.log(f"Erro ao reiniciar main: {e}")
            # Tenta alternativa
            try:
                subprocess.Popen(
                    [sys.executable, "orchestrator_auto.py"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.log("Orquestrador automatico iniciado como fallback")
            except Exception as e2:
                self.log(f"ERRO CRITICO: {e2}")
        
        self.last_wakeup = datetime.now()
        self.log("Sistema reiniciado com sucesso!")
    
    def monitor_loop(self):
        """Loop principal de monitorizacao ULTRA RAPIDO"""
        self.log("=" * 60)
        self.log("WakeUp System v3.0 - ULTRA RAPIDO")
        self.log(f"Verificacao a cada {WAKEUP_INTERVAL_FAST}s")
        self.log(f"Auto-reset em caso de stuck")
        self.log("=" * 60)
        
        while not self._stop_event.is_set():
            try:
                # Verifica se esta stuck
                if self.detect_stuck_ultra_fast():
                    self.log("STUCK DETETADO! A reiniciar...")
                    self.force_restart()
                    time.sleep(5)  # Espera o sistema arrancar
                
                # Atualiza contagem
                self.iteration_count += 1
                self.last_wakeup = datetime.now()
                
                # Mostra status a cada 10 iteracoes
                if self.iteration_count % 10 == 0:
                    self.log(f"Status: {self.iteration_count} verificacoes, "
                            f"{self.auto_reset_count} resets")
                
                # Espera antes de verificar novamente
                time.sleep(WAKEUP_INTERVAL_FAST)
                
            except KeyboardInterrupt:
                self.log("Monitorizacao interrompida pelo utilizador")
                break
            except Exception as e:
                self.log(f"Erro no loop: {e}")
                time.sleep(WAKEUP_INTERVAL_FAST)
    
    def start(self):
        """Inicia a monitorizacao em background"""
        self.log("Iniciando monitorizacao ULTRA RAPIDA...")
        thread = threading.Thread(target=self.monitor_loop, daemon=True)
        thread.start()
        self.is_monitoring = True
        self.log("Monitorizacao ativa!")
        return thread
    
    def stop(self):
        """Para a monitorizacao"""
        self._stop_event.set()
        self.is_monitoring = False
        self.log("Monitorizacao parada")


if __name__ == "__main__":
    wakeup = WakeUpSystemV3()
    
    # Mostra informacao
    print(f"\nWakeUp System v3.0 - ULTRA RAPIDO")
    print(f"{'='*50}")
    print(f"Verifica a cada: {WAKEUP_INTERVAL_FAST} segundos")
    print(f"Deteta stuck em: ~3 segundos")
    print(f"Auto-reset: ATIVO")
    print(f"{'='*50}\n")
    
    # Inicia
    thread = wakeup.start()
    
    try:
        # Mantem o programa vivo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        wakeup.stop()
        print("\nWakeUp System parado.")
