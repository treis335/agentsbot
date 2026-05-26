"""
Gestor de Auto-Recuperação v3.0 - CORREOTO ECOSYSTEM
- SEM limites de iterações (corre para sempre)
- Monitoriza e reinicia automaticamente
- Integração total com o ecossistema
"""

import asyncio
import json
import os
import sys
import time
import threading
from datetime import datetime
from auto_recovery import AutoRecoverySystem, TaskRunner

# Configurações - SEM LIMITES!
CONFIG = {
    "max_iterations": None,      # SEM limite (None = infinito)
    "cooldown_seconds": 15,      # Tempo entre verificações
    "max_retries": None,         # SEM limite (None = infinito)
    "check_interval": 5,         # Intervalo entre verificações (segundos)
    "log_file": "auto_recovery_manager.log"
}

class AutoRecoveryManager:
    """
    Gestor principal que monitoriza todo o ecossistema
    e reinicia agentes/tarefas quando necessário.
    CORRE PARA SEMPRE - sem limites de iterações.
    """
    
    def __init__(self, config=None):
        self.config = config or CONFIG
        self.recovery = AutoRecoverySystem(
            max_iterations=self.config.get('max_iterations'),  # None = infinito
            cooldown_seconds=self.config.get('cooldown_seconds', 15),
            max_retries=self.config.get('max_retries')  # None = infinito
        )
        self.runner = TaskRunner(self.recovery)
        self.active_tasks = {}
        self.monitoring = False
        self.thread = None
        
    def monitor_loop(self):
        """
        Loop principal de monitorização.
        Corre para SEMPRE - nunca para.
        """
        self.monitoring = True
        print("=" * 60)
        print("🔍 CORREOTO AUTO-RECOVERY MANAGER v3.0")
        print("📊 Modo: INFINITO (nunca para)")
        print(f"⏳ Intervalo: {self.config.get('cooldown_seconds', 15)}s")
        print("=" * 60)
        
        iteration = 0
        while self.monitoring:
            try:
                iteration += 1
                
                # Executa recuperação
                status = self.recovery.get_status()
                
                # Mostra estado periódicamente
                if iteration % 6 == 0:  # A cada ~minuto
                    print(f"\n📊 [Ciclo #{iteration}] Estado do ecossistema:")
                    print(f"   🔄 Iterações: {status['iterations']}")
                    print(f"   ❤️  Componentes: {sum(1 for c in status['components'].values() if c['status'] == 'ok')}/{len(status['components'])} ok")
                    print(f"   🔧 Recuperações: {status['recovery_count']}")
                
                # Executa recovery
                self.recovery.recover()
                
                time.sleep(self.config.get('cooldown_seconds', 15))
                
            except KeyboardInterrupt:
                print("\n🛑 Monitorização interrompida pelo utilizador")
                break
            except Exception as e:
                print(f"❌ Erro no monitor loop: {e}")
                time.sleep(5)
    
    def start_monitoring(self):
        """Inicia a monitorização em background"""
        if self.thread and self.thread.is_alive():
            print("⚠️ Monitorização já está em execução")
            return
        
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()
        print("✅ Monitorização iniciada em background (nunca para)")
    
    def stop_monitoring(self):
        """Para a monitorização"""
        self.monitoring = False
        print("🛑 Monitorização parada")
    
    def get_full_status(self):
        """Retorna estado completo do sistema"""
        return {
            "recovery": self.recovery.get_status(),
            "active_tasks": len(self.active_tasks),
            "monitoring": self.monitoring,
            "config": self.config
        }


if __name__ == "__main__":
    manager = AutoRecoveryManager()
    
    try:
        print("🚀 A iniciar AutoRecoveryManager em modo INFINITO...")
        manager.start_monitoring()
        
        # Mantém o processo vivo
        while True:
            time.sleep(10)
            status = manager.get_full_status()
            print(f"💚 Sistema vivo | Iterações: {status['recovery']['iterations']} | Recuperações: {status['recovery']['recovery_count']}")
            
    except KeyboardInterrupt:
        print("\n👋 AutoRecoveryManager encerrado")
        manager.stop_monitoring()
