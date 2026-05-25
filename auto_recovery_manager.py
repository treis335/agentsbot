"""
Gestor de Auto-Recuperação - Integração com o ecossistema Correoto
Monitoriza e reinicia automaticamente quando atinge limites de iterações
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from auto_recovery import AutoRecoverySystem, TaskRunner

# Configurações
CONFIG = {
    "max_iterations": 8,        # Limite de iterações antes de pausar
    "cooldown_seconds": 30,     # Tempo de pausa inicial
    "max_retries": 5,           # Máximo de tentativas
    "check_interval": 5,        # Intervalo entre verificações (segundos)
    "log_file": "auto_recovery_manager.log"
}

class AutoRecoveryManager:
    """
    Gestor principal que monitoriza todo o ecossistema
    e reinicia agentes/tarefas quando necessário
    """
    
    def __init__(self, config=None):
        self.config = config or CONFIG
        self.recovery = AutoRecoverySystem(
            max_iterations=self.config['max_iterations'],
            cooldown_seconds=self.config['cooldown_seconds'],
            max_retries=self.config['max_retries']
        )
        self.runner = TaskRunner(self.recovery)
        self.active_tasks = {}
        self.monitoring = False
        
    async def monitor_loop(self):
        """
        Loop principal de monitorização.
        Corre em background e verifica o estado do sistema.
        """
        self.monitoring = True
        print("🔍 Sistema de monitorização ativo!")
        print(f"📊 Limite: {self.config['max_iterations']} iterações")
        print(f"⏳ Cooldown: {self.config['cooldown_seconds']}s")
        print(f"🔄 Máx tentativas: {self.config['max_retries']}")
        print("-" * 50)
        
        while self.monitoring:
            try:
                # Verifica estado atual
                status = self.recovery.get_status()
                
                # Se aproximando do limite, avisa
                remaining = self.config['max_iterations'] - status['iterations']
                if remaining <= 3 and remaining > 0:
                    print(f"⚠️ Atenção: {remaining} iterações restantes antes do cooldown!")
                
                # Se atingiu o limite, faz pausa automática
                if self.recovery.check_iteration_limit():
                    print(f"⏸️ Limite atingido! A pausar por {self.config['cooldown_seconds']}s...")
                    await self.recovery.cooldown()
                    self.recovery.reset()
                    print("▶️ Sistema retomado!")
                
                await asyncio.sleep(self.config['check_interval'])
                
            except KeyboardInterrupt:
                print("\n🛑 Monitorização interrompida pelo utilizador")
                self.monitoring = False
                break
            except Exception as e:
                print(f"❌ Erro na monitorização: {e}")
                await asyncio.sleep(10)  # Espera mais tempo após erro
    
    async def execute_with_protection(self, task_func, task_name="tarefa", *args, **kwargs):
        """
        Executa uma tarefa com proteção contra limites de iterações
        
        Args:
            task_func: Função a executar
            task_name: Nome da tarefa
            *args, **kwargs: Argumentos
        """
        print(f"🚀 A executar '{task_name}' com proteção...")
        
        result = await self.runner.run_with_recovery(
            task_func, 
            task_name=task_name,
            *args, 
            **kwargs
        )
        
        return result
    
    def get_full_status(self):
        """Devolve o estado completo do sistema"""
        return {
            'recovery': self.recovery.get_status(),
            'active_tasks': list(self.active_tasks.keys()),
            'monitoring': self.monitoring,
            'config': self.config,
            'timestamp': datetime.now().isoformat()
        }
    
    def stop(self):
        """Para o sistema de monitorização"""
        self.monitoring = False
        print("🛑 Sistema de monitorização parado")


# Funções de exemplo para testar
async def tarefa_pesada():
    """Simula uma tarefa que pode atingir limites"""
    for i in range(15):
        print(f"📝 Passo {i+1}/15...")
        await asyncio.sleep(1)
    return "✅ Tarefa pesada concluída!"


async def main():
    """Função principal"""
    print("=" * 60)
    print("🤖 SISTEMA DE AUTO-RECUPERAÇÃO CORREOTO")
    print("=" * 60)
    print()
    
    # Cria o gestor
    manager = AutoRecoveryManager()
    
    # Inicia monitorização em background
    monitor_task = asyncio.create_task(manager.monitor_loop())
    
    # Executa uma tarefa de exemplo
    print("\n📋 A executar tarefa de teste...")
    resultado = await manager.execute_with_protection(
        tarefa_pesada,
        task_name="teste_pesado"
    )
    
    print(f"\n📊 Resultado: {resultado}")
    print(f"\n📋 Estado final:")
    print(json.dumps(manager.get_full_status(), indent=2, ensure_ascii=False))
    
    # Para tudo
    manager.stop()
    monitor_task.cancel()
    
    print("\n✅ Sistema concluído!")


if __name__ == "__main__":
    asyncio.run(main())
