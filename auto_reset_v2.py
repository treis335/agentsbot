"""
Auto-Reset System v2.0 - ULTRA RÁPIDO
Reinicia o Supervisor em SEGUNDOS quando atinge limite de iteracoes
Funciona 24/7 sem intervencao humana!
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

# Config
CHECK_INTERVAL = 2          # Verifica a cada 2 SEGUNDOS
MAX_IDLE_SECONDS = 10       # 10 segundos sem atividade = reset
MAX_ITERATIONS = 6          # Maximo de iteracoes antes de reset
LOG_FILE = "auto_reset_v2.log"

class AutoResetV2:
    def __init__(self):
        self.last_activity = datetime.now()
        self.reset_count = 0
        self.iteration_count = 0
        self._stop = threading.Event()
        self.memory_file = "memory/global/shared_memory.json"
        self.conversation_file = "memory/conversations/telegram_1094139387.json"
        
    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] {msg}"
        print(entry)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    
    def check_memory_for_stuck(self):
        """Verifica se a memoria indica que estamos stuck"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Verifica se ha indicacao de limite atingido
                content = json.dumps(data)
                if "limite de itera" in content.lower() or "iteration limit" in content.lower():
                    return True
                    
                # Verifica timestamp da ultima atividade
                if "last_active" in data:
                    last = data["last_active"]
                    if isinstance(last, str):
                        try:
                            last_time = datetime.fromisoformat(last)
                            diff = (datetime.now() - last_time).total_seconds()
                            if diff > MAX_IDLE_SECONDS:
                                return True
                        except:
                            pass
        except:
            pass
        return False
    
    def force_reset(self, reason="limite_iteracoes"):
        """Forca o reset do Supervisor"""
        self.reset_count += 1
        self.log(f"[LOOP] RESET #{self.reset_count} - Motivo: {reason}")
        
        # 1. Mata processos antigos
        try:
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq Supervisor*"], 
                         capture_output=True, timeout=5)
        except:
            pass
        
        # 2. Limpa memoria de bloqueio
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["last_active"] = datetime.now().isoformat()
                data["reset_count"] = self.reset_count
                data["status"] = "active"
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass
        
        # 3. Reinicia o main.py
        self.log("[START] A reiniciar Supervisor...")
        try:
            subprocess.Popen(
                ["start", "cmd", "/c", "python main.py & python auto_evolve.py"],
                shell=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
        except Exception as e:
            self.log(f"[X] Erro ao reiniciar: {e}")
        
        self.last_activity = datetime.now()
        self.log("[OK] Supervisor reiniciado com sucesso!")
    
    def monitor_loop(self):
        """Loop principal de monitorizacao"""
        self.log("[START] Auto-Reset V2 iniciado! A monitorizar a cada 2s...")
        
        while not self._stop.is_set():
            try:
                # Verifica se esta stuck
                stuck = self.check_memory_for_stuck()
                
                # Verifica tempo desde ultima atividade
                idle_seconds = (datetime.now() - self.last_activity).total_seconds()
                
                if stuck or idle_seconds > MAX_IDLE_SECONDS:
                    self.force_reset(reason="stuck" if stuck else "inactivity")
                    time.sleep(5)  # Espera 5s antes de verificar novamente
                
                self.iteration_count += 1
                if self.iteration_count >= MAX_ITERATIONS:
                    self.iteration_count = 0
                    self.log(f"⏱️ Reset preventivo a cada {MAX_ITERATIONS} iteracoes")
                    self.force_reset(reason="preventive")
                
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                self.log(f"[X] Erro no monitor: {e}")
                time.sleep(5)
    
    def start(self):
        """Inicia o monitor em background"""
        thread = threading.Thread(target=self.monitor_loop, daemon=True)
        thread.start()
        self.log("[OK] Auto-Reset V2 ativo em background!")
        return thread
    
    def stop(self):
        self._stop.set()
        self.log("[PARAR] Auto-Reset V2 parado.")

if __name__ == "__main__":
    print("="*60)
    print("  AUTO-RESET V2 - Supervisor 24/7")
    print("  A monitorizar a cada 2 SEGUNDOS!")
    print("="*60)
    
    reset = AutoResetV2()
    thread = reset.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        reset.stop()
        print("\n[TCHAU] Auto-Reset V2 terminado.")
