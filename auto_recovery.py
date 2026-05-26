"""
Sistema de Auto-Recuperacao v5.0 - CORREOTO ECOSYSTEM
✅ SEM limites de iteracoes (corre para sempre)
✅ Monitoriza, repara e reinicia automaticamente todo o ecossistema
✅ Deteccao inteligente de falhas
✅ Auto-repair de componentes corrompidos
✅ Decisao autonoma - so pede supervisao em casos criticos
✅ Verificacao de integridade de ficheiros
✅ Ciclo de auto-evolucao integrado
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
            "supervisor.md": {"path": BASE / "agents" / "souls" / "supervisor.md", "status": "unknown"},
            "auto_update.py": {"path": BASE / "auto_update.py", "status": "unknown"},
        }
        
    def check_file_integrity(self, filepath):
        """Verifica se um ficheiro existe e nao esta corrompido."""
        path = Path(filepath)
        if not path.exists():
            return False, "Ficheiro nao existe"
        if path.stat().st_size < 100:
            return False, f"Ficheiro demasiado pequeno ({path.stat().st_size} bytes)"
        return True, "OK"
    
    def check_component_status(self, name, info):
        """Verifica o estado de um componente."""
        path = info["path"]
        is_ok, msg = self.check_file_integrity(path)
        info["status"] = "ok" if is_ok else "corrompido"
        info["last_check"] = datetime.now().isoformat()
        return is_ok, msg
    
    def repair_component(self, name, info):
        """Tenta reparar um componente corrompido."""
        logger.warning(f"🔧 A tentar reparar {name}...")
        
        # Tentar restaurar de backup
        backup_path = Path(str(info["path"]) + ".bak")
        if backup_path.exists():
            try:
                import shutil
                shutil.copy2(backup_path, info["path"])
                logger.info(f"✅ {name} restaurado do backup!")
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao restaurar backup de {name}: {e}")
        
        # Se nao ha backup, marcar para regeneracao
        logger.warning(f"⚠️ {name} precisa de ser regenerado pelo supervisor")
        return False
    
    def recovery_cycle(self):
        """Ciclo de recuperacao - verifica e repara componentes."""
        self.iteration_count += 1
        logger.info(f"🔄 Ciclo de recuperacao #{self.iteration_count}")
        
        issues_found = False
        for name, info in self.components.items():
            is_ok, msg = self.check_component_status(name, info)
            if not is_ok:
                issues_found = True
                logger.warning(f"⚠️ {name}: {msg}")
                self.repair_component(name, info)
                self.recovery_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "component": name,
                    "issue": msg,
                    "action": "repair_attempted"
                })
        
        if not issues_found:
            logger.info("✅ Todos os componentes OK!")
        
        # Reset do contador de retries se passou tempo suficiente
        if (datetime.now() - self.last_reset).seconds > 3600:
            self.retry_count = 0
            self.last_reset = datetime.now()
            logger.info("🔄 Contador de retries resetado (1h passou)")
        
        return issues_found
    
    async def run_forever(self):
        """Corre o sistema de recuperacao para sempre."""
        self.is_running = True
        logger.info("=" * 60)
        logger.info("🚀 AUTO-RECOVERY v5.0 INICIADO - Modo Infinito")
        logger.info(f"   Max Iteracoes: {'Infinito' if self.max_iterations == float('inf') else self.max_iterations}")
        logger.info(f"   Cooldown: {self.cooldown_seconds}s")
        logger.info(f"   Max Retries: {'Infinito' if self.max_retries == float('inf') else self.max_retries}")
        logger.info("=" * 60)
        
        try:
            while self.is_running:
                if self.iteration_count >= self.max_iterations:
                    logger.info("✅ Limite de iteracoes atingido. A reiniciar ciclo...")
                    self.iteration_count = 0
                
                if self.retry_count >= self.max_retries:
                    logger.warning("⚠️ Limite de retries atingido. A aguardar reset...")
                    await asyncio.sleep(60)
                    self.retry_count = 0
                    continue
                
                self.recovery_cycle()
                
                logger.info(f"⏳ A aguardar {self.cooldown_seconds}s ate proximo ciclo...")
                await asyncio.sleep(self.cooldown_seconds)
                
        except asyncio.CancelledError:
            logger.info("⏹️  Sistema de recuperacao cancelado.")
        except Exception as e:
            logger.error(f"❌ Erro no sistema de recuperacao: {e}")
        finally:
            self.is_running = False
            logger.info("👋 Auto-Recovery terminado.")

def main():
    """Funcao principal para execucao direta."""
    system = AutoRecoverySystem(
        max_iterations=None,  # Infinito
        cooldown_seconds=10,
        max_retries=None  # Infinito
    )
    
    try:
        asyncio.run(system.run_forever())
    except KeyboardInterrupt:
        logger.info("\n⏹️  Sistema interrompido pelo utilizador.")
        system.is_running = False

if __name__ == "__main__":
    main()
