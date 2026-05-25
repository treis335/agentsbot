"""
Sistema de Auto-Recuperacao para o ecossistema Correoto
Monitoriza e reinicia automaticamente quando atinge limites de iteracoes
"""

import asyncio
import time
import logging
import sys
import os
from datetime import datetime, timedelta

# Configuracao de logging sem emojis (compativel com Windows)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_recovery.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AutoRecovery')

class AutoRecoverySystem:
    """
    Sistema que monitoriza o estado do ecossistema e reinicia
    automaticamente quando atinge limites de iteracoes.
    """
    
    def __init__(self, max_iterations=10, cooldown_seconds=30, max_retries=5):
        self.max_iterations = max_iterations
        self.cooldown_seconds = cooldown_seconds
        self.max_retries = max_retries
        self.iteration_count = 0
        self.retry_count = 0
        self.last_reset = datetime.now()
        self.is_running = False
        self.recovery_history = []
        
    def check_iteration_limit(self):
        """Verifica se o limite de iteracoes foi atingido"""
        self.iteration_count += 1
        
        if self.iteration_count >= self.max_iterations:
            logger.warning(f"Limite de {self.max_iterations} iteracoes atingido!")
            return True
        return False
    
    async def cooldown(self):
        """Aguarda o tempo de cooldown antes de reiniciar"""
        wait_time = self.cooldown_seconds * (self.retry_count + 1)  # Backoff exponencial
        logger.info(f"Cooldown de {wait_time}s antes de reiniciar...")
        
        for i in range(wait_time, 0, -1):
            sys.stdout.write(f"\rA reiniciar em {i}s... ")
            sys.stdout.flush()
            await asyncio.sleep(1)
        
        print()  # Nova linha
        logger.info("Cooldown concluido!")
    
    async def recover(self, task_name="tarefa"):
        """
        Tenta recuperar de um limite de iteracoes
        
        Args:
            task_name: Nome da tarefa que estava a ser executada
        """
        if self.retry_count >= self.max_retries:
            logger.error(f"Maximo de {self.max_retries} tentativas atingido para '{task_name}'")
            self.recovery_history.append({
                'task': task_name,
                'status': 'failed',
                'timestamp': datetime.now().isoformat(),
                'retries': self.retry_count
            })
            return False
        
        self.retry_count += 1
        self.iteration_count = 0  # Reset do contador de iteracoes
        
        logger.info(f"Tentativa {self.retry_count}/{self.max_retries} de recuperacao para '{task_name}'")
        
        await self.cooldown()
        
        self.recovery_history.append({
            'task': task_name,
            'status': 'recovered',
            'timestamp': datetime.now().isoformat(),
            'attempt': self.retry_count
        })
        
        return True
    
    def reset(self):
        """Reseta todos os contadores"""
        self.iteration_count = 0
        self.retry_count = 0
        self.last_reset = datetime.now()
        logger.info("Sistema resetado com sucesso!")
    
    def get_status(self):
        """Devolve o estado atual do sistema"""
        return {
            'iterations': self.iteration_count,
            'max_iterations': self.max_iterations,
            'retries': self.retry_count,
            'max_retries': self.max_retries,
            'last_reset': self.last_reset.isoformat(),
            'is_running': self.is_running,
            'recovery_history': self.recovery_history[-10:]  # Ultimas 10 recuperacoes
        }


class TaskRunner:
    """
    Runner de tarefas com auto-recuperacao
    """
    
    def __init__(self, recovery_system=None):
        self.recovery = recovery_system or AutoRecoverySystem()
        self.task_queue = asyncio.Queue()
        self.results = {}
        
    async def run_with_recovery(self, task_func, task_name="tarefa", *args, **kwargs):
        """
        Executa uma funcao com monitorizacao de iteracoes e recuperacao automatica
        
        Args:
            task_func: Funcao assincrona a executar
            task_name: Nome da tarefa
            *args, **kwargs: Argumentos para a funcao
        """
        self.recovery.is_running = True
        
        while True:
            try:
                # Verifica limite de iteracoes
                if self.recovery.check_iteration_limit():
                    recovered = await self.recovery.recover(task_name)
                    if not recovered:
                        logger.error(f"Tarefa '{task_name}' falhou apos todas as tentativas")
                        self.results[task_name] = {
                            'status': 'failed',
                            'error': 'Max retries exceeded'
                        }
                        return False
                    continue  # Tenta novamente
                
                # Executa a tarefa
                logger.info(f"A executar '{task_name}'...")
                result = await task_func(*args, **kwargs)
                
                self.results[task_name] = {
                    'status': 'success',
                    'result': result
                }
                
                logger.info(f"Tarefa '{task_name}' concluida com sucesso!")
                return result
                
            except Exception as e:
                logger.error(f"Erro em '{task_name}': {str(e)}")
                
                # Tenta recuperar
                recovered = await self.recovery.recover(task_name)
                if not recovered:
                    self.results[task_name] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    return None
                
                # Pequena pausa antes de tentar novamente
                await asyncio.sleep(2)
        
        self.recovery.is_running = False


# Exemplo de uso
async def exemplo_tarefa():
    """Exemplo de tarefa que simula trabalho"""
    print("A executar tarefa de exemplo...")
    await asyncio.sleep(2)
    return "Tarefa concluida!"


async def main():
    """Funcao principal de exemplo"""
    print("=" * 60)
    print("SISTEMA DE AUTO-RECUPERACAO CORREOTO")
    print("=" * 60)
    
    # Cria o sistema
    recovery = AutoRecoverySystem(max_iterations=5, cooldown_seconds=10)
    runner = TaskRunner(recovery)
    
    # Executa uma tarefa de exemplo
    resultado = await runner.run_with_recovery(
        exemplo_tarefa,
        task_name="exemplo"
    )
    
    print(f"\nResultado: {resultado}")
    print(f"Estado: {recovery.get_status()}")
    
    return resultado


if __name__ == "__main__":
    asyncio.run(main())
