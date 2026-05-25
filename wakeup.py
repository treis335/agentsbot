"""
Wake-Up System para o ecossistema Correoto
Acorda automaticamente quando atinge limite de iteracoes
Tempo de wake-up: 1 minuto
"""

import asyncio
import subprocess
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

# Configuracoes
WAKEUP_INTERVAL = 60  # 1 minuto em segundos
MAX_ITERATIONS = 10
LOG_FILE = "wakeup.log"

class WakeUpSystem:
    """
    Sistema que monitoriza o ecossistema e acorda automaticamente
    quando o supervisor atinge o limite de iteracoes.
    """
    
    def __init__(self):
        self.iteration_count = 0
        self.last_wakeup = datetime.now()
        self.is_monitoring = False
        self.wakeup_history = []
        
    def log(self, message):
        """Regista mensagem no log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def check_if_stuck(self):
        """Verifica se o sistema esta preso (limite de iteracoes)"""
        # Verifica se ha ficheiros de log recentes com "Limite de iteracoes"
        try:
            if os.path.exists("auto_recovery.log"):
                with open("auto_recovery.log", "r", encoding="utf-8") as f:
                    content = f.read()
                    if "Limite de iteracoes atingido" in content:
                        return True
        except:
            pass
        
        # Verifica se o processo principal ainda esta a correr
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe"],
                capture_output=True, text=True, timeout=5
            )
            # Se nao houver processos python, esta preso
            if "python.exe" not in result.stdout:
                return True
        except:
            pass
            
        return False
    
    def restart_system(self):
        """Reinicia o sistema principal"""
        self.log("🔄 A reiniciar o sistema...")
        
        # Mata processos python antigos (exceto este)
        try:
            subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                         capture_output=True, timeout=5)
            self.log("✅ Processos python antigos mortos")
        except:
            pass
        
        # Aguarda um momento
        time.sleep(2)
        
        # Inicia o main.py novamente
        try:
            subprocess.Popen(
                [sys.executable, "main.py"],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.log("✅ Sistema reiniciado com sucesso!")
            return True
        except Exception as e:
            self.log(f"❌ Erro ao reiniciar: {e}")
            return False
    
    async def monitor_loop(self):
        """Loop principal de monitorizacao - acorda a cada 1 minuto"""
        self.is_monitoring = True
        self.log("=" * 60)
        self.log("🚀 SISTEMA DE WAKE-UP INICIADO")
        self.log(f"⏰ A acordar a cada {WAKEUP_INTERVAL}s (1 minuto)")
        self.log(f"🔄 Max iteracoes: {MAX_ITERATIONS}")
        self.log("=" * 60)
        
        while self.is_monitoring:
            try:
                self.iteration_count += 1
                now = datetime.now()
                
                self.log(f"\n📊 Verificacao #{self.iteration_count} - {now.strftime('%H:%M:%S')}")
                
                # Verifica se esta preso
                if self.check_if_stuck():
                    self.log("⚠️ SISTEMA PRESO DETETADO!")
                    self.wakeup_history.append({
                        "time": now.isoformat(),
                        "iteration": self.iteration_count,
                        "action": "restart"
                    })
                    
                    if self.restart_system():
                        self.log("✅ Sistema recuperado com sucesso!")
                    else:
                        self.log("❌ Falha na recuperacao - a tentar novamente...")
                        time.sleep(5)
                        self.restart_system()
                else:
                    self.log("✅ Sistema operacional - tudo normal")
                    self.wakeup_history.append({
                        "time": now.isoformat(),
                        "iteration": self.iteration_count,
                        "action": "check_ok"
                    })
                
                # Guarda historico
                self.save_history()
                
                # Aguarda 1 minuto
                self.log(f"⏳ A dormir por {WAKEUP_INTERVAL}s...")
                await asyncio.sleep(WAKEUP_INTERVAL)
                
            except KeyboardInterrupt:
                self.log("👋 Sistema de wake-up desligado pelo utilizador")
                break
            except Exception as e:
                self.log(f"❌ Erro no monitor: {e}")
                await asyncio.sleep(10)
    
    def save_history(self):
        """Guarda historico de wake-ups"""
        history_file = "wakeup_history.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump({
                    "last_update": datetime.now().isoformat(),
                    "total_wakeups": self.iteration_count,
                    "history": self.wakeup_history[-100:]  # Ultimos 100
                }, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def get_status(self):
        """Devolve estado atual do sistema"""
        return {
            "status": "running" if self.is_monitoring else "stopped",
            "total_checks": self.iteration_count,
            "last_check": self.wakeup_history[-1] if self.wakeup_history else None,
            "uptime": str(datetime.now() - self.last_wakeup)
        }

async def main():
    """Ponto de entrada principal"""
    wakeup = WakeUpSystem()
    
    print("""
    ╔══════════════════════════════════════════╗
    ║     🚀 SISTEMA DE WAKE-UP CORREOTO      ║
    ║     Acorda a cada 1 minuto!              ║
    ╚══════════════════════════════════════════╝
    """)
    
    await wakeup.monitor_loop()

if __name__ == "__main__":
    asyncio.run(main())
