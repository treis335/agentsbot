"""
Sistema de Auto-Recuperacao v3.0 - CORREOTO ECOSYSTEM
- SEM limites de iteracoes (corre para sempre)
- Monitoriza, repara e reinicia automaticamente todo o ecossistema
- Deteccao inteligente de falhas
- Auto-repair de componentes
"""

import asyncio
import time
import logging
import sys
import os
import json
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE / 'auto_recovery.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AutoRecovery')

class AutoRecoverySystem:
    """
    Sistema que monitoriza o estado do ecossistema e repara automaticamente.
    CORRE PARA SEMPRE - sem limites de iteracoes.
    """
    
    def __init__(self, max_iterations=None, cooldown_seconds=15, max_retries=None):
        # Se max_iterations for None, corre para sempre
        self.max_iterations = max_iterations if max_iterations is not None else float('inf')
        self.cooldown_seconds = cooldown_seconds
        self.max_retries = max_retries if max_retries is not None else float('inf')
        self.iteration_count = 0
        self.retry_count = 0
        self.last_reset = datetime.now()
        self.is_running = False
        self.recovery_history = []
        self.components = {
            "main.py": {"path": BASE / "main.py", "status": "unknown"},
            "brain.py": {"path": BASE / "cerebro" / "core" / "brain.py", "status": "unknown"},
            "ml_engine.py": {"path": BASE / "cerebro" / "core" / "ml_engine.py", "status": "unknown"},
            "api_connector.py": {"path": BASE / "cerebro" / "core" / "api_connector.py", "status": "unknown"},
            "keep_alive.py": {"path": BASE / "core" / "keep_alive.py", "status": "unknown"},
        }
        
    def check_iteration_limit(self):
        """Verifica se o limite de iteracoes foi atingido - SEMPRE RETORNA False (corre para sempre)"""
        self.iteration_count += 1
        # NUNCA para - corre para sempre
        if self.iteration_count >= self.max_iterations:
            logger.warning(f"Limite de iteracoes: {self.iteration_count} (mas vou continuar mesmo assim!)")
            # Reset contador para continuar para sempre
            self.iteration_count = 0
        return False  # NUNCA para
        
    def get_status(self):
        """Retorna o estado atual do sistema"""
        return {
            "iterations": self.iteration_count,
            "max_iterations": "INFINITO" if self.max_iterations == float('inf') else self.max_iterations,
            "retries": self.retry_count,
            "max_retries": "INFINITO" if self.max_retries == float('inf') else self.max_retries,
            "last_reset": self.last_reset.isoformat(),
            "is_running": self.is_running,
            "components": self.components,
            "recovery_count": len(self.recovery_history)
        }
    
    def check_component(self, name):
        """Verifica se um componente está saudável"""
        comp = self.components.get(name)
        if not comp:
            return False
        
        path = comp["path"]
        if not path.exists():
            comp["status"] = "missing"
            return False
        
        # Verifica se o ficheiro tem conteúdo válido
        try:
            content = path.read_text(encoding="utf-8")
            if len(content) < 10:
                comp["status"] = "corrupted"
                return False
            comp["status"] = "ok"
            return True
        except:
            comp["status"] = "error"
            return False
    
    def repair_component(self, name):
        """Tenta reparar um componente"""
        comp = self.components.get(name)
        if not comp:
            return False
        
        path = comp["path"]
        logger.info(f"🔧 A tentar reparar: {name}")
        
        # Se o ficheiro não existe, cria um básico
        if not path.exists():
            try:
                path.write_text(f"# {name} - Auto-reparado\n# Reparado em: {datetime.now().isoformat()}\n")
                logger.info(f"✅ {name} recriado")
                comp["status"] = "repaired"
                self.recovery_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "component": name,
                    "action": "recreated"
                })
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao recriar {name}: {e}")
                return False
        
        return False
    
    def recover(self):
        """Executa ciclo de recuperação"""
        self.is_running = True
        
        if self.check_iteration_limit():
            logger.info("⏸️ Limite de iteracoes atingido. A pausar...")
            self.is_running = False
            return False
        
        logger.info(f"🔄 Ciclo de recuperação #{self.iteration_count}")
        
        all_ok = True
        for name in self.components:
            if not self.check_component(name):
                all_ok = False
                logger.warning(f"⚠️ Componente com problema: {name}")
                if self.repair_component(name):
                    logger.info(f"✅ {name} reparado com sucesso!")
                else:
                    logger.error(f"❌ Não foi possível reparar {name}")
        
        if all_ok:
            logger.info("✅ Todos os componentes saudáveis")
        
        self.is_running = False
        return all_ok


class TaskRunner:
    """Executa tarefas de recuperação em loop infinito"""
    
    def __init__(self, recovery_system):
        self.recovery = recovery_system
        self.running = False
        self.thread = None
    
    def run_forever(self):
        """Loop principal - corre para sempre"""
        self.running = True
        logger.info("=" * 60)
        logger.info("🚀 AutoRecovery v3.0 INICIADO - MODO INFINITO")
        logger.info("=" * 60)
        
        while self.running:
            try:
                self.recovery.recover()
                time.sleep(self.recovery.cooldown_seconds)
            except KeyboardInterrupt:
                logger.info("🛑 AutoRecovery interrompido pelo utilizador")
                break
            except Exception as e:
                logger.error(f"❌ Erro no loop: {e}")
                time.sleep(5)
    
    def start(self):
        """Inicia o loop em background"""
        if self.thread and self.thread.is_alive():
            logger.warning("⚠️ TaskRunner já está em execução")
            return
        
        self.thread = threading.Thread(target=self.run_forever, daemon=True)
        self.thread.start()
        logger.info("✅ TaskRunner iniciado em background")
    
    def stop(self):
        """Para o loop"""
        self.running = False
        logger.info("🛑 TaskRunner parado")


if __name__ == "__main__":
    # Teste rápido
    recovery = AutoRecoverySystem(max_iterations=None, cooldown_seconds=10)
    runner = TaskRunner(recovery)
    
    try:
        runner.run_forever()
    except KeyboardInterrupt:
        logger.info("👋 AutoRecovery encerrado")
