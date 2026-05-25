"""
Orquestrador Automatico - Coracao do ecossistema Correoto
Coordena: WakeUp + AutoRecovery + AutoEvolve
Faz tudo funcionar autonomamente!
"""

import asyncio
import subprocess
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

class OrchestratorAuto:
    """
    Orquestrador que coordena todos os sistemas automaticos:
    - WakeUp (acorda a cada 1 minuto)
    - AutoRecovery (recupera de falhas)
    - AutoEvolve (aprende e evolui)
    """
    
    def __init__(self):
        self.processes = {}
        self.status = {
            "wakeup": False,
            "auto_recovery": False,
            "auto_evolve": False,
            "main": False
        }
        self.start_time = datetime.now()
        
    def log(self, message):
        """Regista mensagem"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 🎯 {message}")
        
        with open("orchestrator.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def start_process(self, name, script, args=None):
        """Inicia um processo em segundo plano"""
        try:
            cmd = [sys.executable, script]
            if args:
                cmd.extend(args)
            
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes[name] = process
            self.status[name] = True
            self.log(f"✅ Processo '{name}' iniciado (PID: {process.pid})")
            return process
            
        except Exception as e:
            self.log(f"❌ Erro ao iniciar '{name}': {e}")
            return None
    
    def stop_process(self, name):
        """Para um processo"""
        if name in self.processes and self.processes[name]:
            try:
                self.processes[name].terminate()
                self.status[name] = False
                self.log(f"⏹️ Processo '{name}' parado")
            except:
                pass
    
    def check_processes(self):
        """Verifica se todos os processos estao a correr"""
        for name, process in list(self.processes.items()):
            if process and process.poll() is not None:
                self.log(f"⚠️ Processo '{name}' morreu (codigo: {process.returncode})")
                self.status[name] = False
                
                # Tenta reiniciar
                if name == "wakeup":
                    self.start_process("wakeup", "wakeup.py")
                elif name == "auto_evolve":
                    self.start_process("auto_evolve", "auto_evolve.py")
                elif name == "main":
                    self.start_process("main", "main.py")
    
    def get_system_status(self):
        """Devolve estado completo do sistema"""
        uptime = datetime.now() - self.start_time
        hours = uptime.total_seconds() / 3600
        
        return {
            "status": "running" if any(self.status.values()) else "stopped",
            "uptime_hours": round(hours, 2),
            "processes": self.status,
            "active_processes": sum(1 for v in self.status.values() if v),
            "total_processes": len(self.status),
            "started_at": self.start_time.isoformat()
        }
    
    async def main_loop(self):
        """Loop principal do orquestrador"""
        print("""
    ╔══════════════════════════════════════════════════╗
    ║     🚀 ORQUESTRADOR AUTOMATICO CORREOTO         ║
    ║     A coordenar todo o ecossistema!             ║
    ╚══════════════════════════════════════════════════╝
        """)
        
        self.log("A iniciar todos os sistemas...")
        
        # Inicia todos os processos
        self.start_process("wakeup", "wakeup.py")
        await asyncio.sleep(2)
        
        self.start_process("auto_evolve", "auto_evolve.py")
        await asyncio.sleep(2)
        
        self.start_process("main", "main.py")
        
        self.log("=" * 60)
        self.log("✅ TODOS OS SISTEMAS INICIADOS!")
        self.log("📊 Status:")
        for name, status in self.status.items():
            self.log(f"   {'✅' if status else '❌'} {name}")
        self.log("=" * 60)
        
        # Loop de monitorizacao
        check_interval = 30  # Verifica a cada 30s
        while True:
            try:
                await asyncio.sleep(check_interval)
                self.check_processes()
                
                # Mostra status a cada 5 minutos
                if int(time.time()) % 300 < check_interval:
                    status = self.get_system_status()
                    self.log(f"📊 Status: {status['active_processes']}/{status['total_processes']} ativos")
                
            except KeyboardInterrupt:
                self.log("👋 A desligar todos os sistemas...")
                for name in list(self.processes.keys()):
                    self.stop_process(name)
                self.log("✅ Todos os sistemas desligados")
                break
            except Exception as e:
                self.log(f"❌ Erro no orquestrador: {e}")
                await asyncio.sleep(10)

async def main():
    """Ponto de entrada"""
    orchestrator = OrchestratorAuto()
    await orchestrator.main_loop()

if __name__ == "__main__":
    asyncio.run(main())
