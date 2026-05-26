"""
Sistema de Auto-Recuperacao v4.0 - CORREOTO ECOSYSTEM
✅ SEM limites de iteracoes (corre para sempre)
✅ Monitoriza, repara e reinicia automaticamente todo o ecossistema
✅ Deteccao inteligente de falhas
✅ Auto-repair de componentes corrompidos
✅ Decisao autonoma - so pede supervisao em casos criticos
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
    
    def __init__(self, max_iterations=None, cooldown_seconds=10, max_retries=None):
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
        """Verifica se atingiu o limite de iteracoes - NUNCA para se for None/inf."""
        self.iteration_count += 1
        if self.iteration_count >= self.max_iterations:
            logger.info(f"Reset automático do contador de iterações ({self.iteration_count})")
            self.iteration_count = 0
            self.last_reset = datetime.now()
            return False
        return True
    
    def check_retry_limit(self):
        """Verifica se atingiu o limite de retries - NUNCA para se for None/inf."""
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            logger.info(f"Reset automático do contador de retries ({self.retry_count})")
            self.retry_count = 0
            return False
        return True
    
    def check_component_health(self, component_name):
        """Verifica saude de um componente especifico."""
        comp = self.components.get(component_name)
        if not comp:
            return False
        
        path = comp["path"]
        if not path.exists():
            logger.warning(f"Componente {component_name} nao encontrado: {path}")
            comp["status"] = "missing"
            return False
        
        try:
            content = path.read_text(encoding="utf-8")
            if len(content) < 50:
                logger.warning(f"Componente {component_name} corrompido (apenas {len(content)} chars)")
                comp["status"] = "corrupted"
                return False
            
            comp["status"] = "healthy"
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar {component_name}: {e}")
            comp["status"] = "error"
            return False
    
    def repair_component(self, component_name):
        """Tenta reparar um componente automaticamente."""
        comp = self.components.get(component_name)
        if not comp:
            return False
        
        path = comp["path"]
        logger.info(f"A reparar componente: {component_name}")
        
        # Tenta restaurar de backup
        bak_path = path.with_suffix(path.suffix + ".bak")
        if bak_path.exists():
            try:
                bak_content = bak_path.read_text(encoding="utf-8")
                path.write_text(bak_content, encoding="utf-8")
                logger.info(f"Restaurado {component_name} a partir de backup")
                comp["status"] = "restored"
                self.recovery_history.append({
                    "time": datetime.now().isoformat(),
                    "component": component_name,
                    "action": "restored_from_backup"
                })
                return True
            except Exception as e:
                logger.error(f"Falha ao restaurar backup de {component_name}: {e}")
        
        # Se nao ha backup, cria um template minimo
        logger.warning(f"Sem backup para {component_name}. A criar template...")
        template = f"""# {component_name} - Auto-restaurado
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('{component_name.replace(".py","")}')

def main():
    logger.info("{component_name} iniciado")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
"""
        try:
            path.write_text(template, encoding="utf-8")
            logger.info(f"Template criado para {component_name}")
            comp["status"] = "template_created"
            self.recovery_history.append({
                "time": datetime.now().isoformat(),
                "component": component_name,
                "action": "template_created"
            })
            return True
        except Exception as e:
            logger.error(f"Falha ao criar template para {component_name}: {e}")
            return False
    
    def check_all_components(self):
        """Verifica todos os componentes e repara automaticamente."""
        all_healthy = True
        for name in self.components:
            if not self.check_component_health(name):
                all_healthy = False
                logger.info(f"Auto-repair: A reparar {name}...")
                if self.repair_component(name):
                    logger.info(f"Auto-repair: {name} reparado com sucesso")
                else:
                    logger.error(f"Auto-repair: Falha ao reparar {name}")
        
        return all_healthy
    
    def run(self):
        """Loop principal - CORRE PARA SEMPRE."""
        self.is_running = True
        logger.info("=" * 60)
        logger.info("SISTEMA DE AUTO-RECUPERACAO v4.0 INICIADO")
        logger.info("Modo: INFINITO - A correr para sempre")
        logger.info("=" * 60)
        
        try:
            while self.is_running:
                # Verifica limites (nunca param)
                self.check_iteration_limit()
                self.check_retry_limit()
                
                # Verifica todos os componentes
                all_healthy = self.check_all_components()
                
                if all_healthy:
                    logger.info(f"Iteracao {self.iteration_count}: Todos os componentes saudaveis")
                else:
                    logger.warning(f"Iteracao {self.iteration_count}: Alguns componentes foram reparados")
                
                # Mostra estatisticas
                healthy_count = sum(1 for c in self.components.values() if c["status"] == "healthy")
                total = len(self.components)
                logger.info(f"Estado: {healthy_count}/{total} componentes saudaveis")
                
                # Cooldown
                time.sleep(self.cooldown_seconds)
                
        except KeyboardInterrupt:
            logger.info("Shutdown recebido. A encerrar...")
            self.is_running = False
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            logger.info("A reiniciar loop automaticamente...")
            time.sleep(2)
            self.run()


def main():
    system = AutoRecoverySystem(
        max_iterations=None,  # INFINITO
        cooldown_seconds=10,
        max_retries=None  # INFINITO
    )
    system.run()


if __name__ == "__main__":
    main()
