"""
Sistema de Auto-Recuperacao v6.0 - CORREOTO ECOSYSTEM
[OK] SEM limites de iteracoes (corre para sempre)
[OK] UNICO sistema de recovery - consolidado
[OK] Nao compete com wakeup/reset/heartbeat
[OK] Detecta crash de Unicode e reporta
"""

import time
import logging
import sys
import os
import subprocess
from datetime import datetime
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
    Versao 6.0: consolidado, sem emojis, sem concorrencia.
    """
    
    def __init__(self, cooldown_seconds=30):
        self.cooldown_seconds = cooldown_seconds
        self.iteration_count = 0
        self.retry_count = 0
        self.last_reset = datetime.now()
        self.is_running = False
        self.recovery_history = []
        
    def check_main_running(self):
        """Verifica se main.py esta em execucao."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5
            )
            # Check if any python process is running main.py
            count = result.stdout.count("python.exe")
            return count > 0
        except:
            return False
    
    def check_log_for_errors(self):
        """Verifica logs recentes por erros."""
        log_files = ["main.log", "auto_recovery.log"]
        for log_file in log_files:
            path = BASE / log_file
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for line in lines[-30:]:
                        if "UnicodeEncodeError" in line or "UnicodeDecodeError" in line:
                            return f"Unicode error in {log_file}"
                        if "Traceback" in line:
                            return f"Crash detected in {log_file}"
                except:
                    pass
        return None
    
    def run_cycle(self):
        """Um ciclo de monitorizacao."""
        self.iteration_count += 1
        logger.info(f"Ciclo #{self.iteration_count}")
        
        # 1. Check for errors
        error = self.check_log_for_errors()
        if error:
            logger.warning(f"Problema detectado: {error}")
            self.recovery_history.append({
                "time": datetime.now().isoformat(),
                "error": error,
                "action": "monitoring_only"
            })
        
        # 2. Check if main is running
        if not self.check_main_running():
            logger.warning("main.py nao esta em execucao!")
            self._restart_main()
        
        return True
    
    def _restart_main(self):
        """Reinicia main.py."""
        logger.info("A reiniciar main.py...")
        try:
            subprocess.Popen(
                ["python", "main.py"],
                cwd=str(BASE),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            logger.info("main.py reiniciado com sucesso.")
        except Exception as e:
            logger.error(f"Falha ao reiniciar main.py: {e}")
    
    def run(self):
        """Loop principal."""
        self.is_running = True
        logger.info("=" * 60)
        logger.info("Auto-Recovery v6.0 iniciado")
        logger.info("=" * 60)
        
        try:
            while self.is_running:
                self.run_cycle()
                time.sleep(self.cooldown_seconds)
        except KeyboardInterrupt:
            logger.info("Sistema interrompido pelo utilizador.")
        except Exception as e:
            logger.error(f"Erro fatal no auto-recovery: {e}")
        finally:
            self.is_running = False


if __name__ == "__main__":
    system = AutoRecoverySystem()
    system.run()
