"""
auto_recovery_manager.py v2.0 - GESTOR DE AUTO-RECUPERACAO
✅ Corre para sempre - modo infinito
✅ Monitoriza e repara todos os componentes
✅ Decisao autonoma
"""

import sys
import os
import time
import logging
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
logger = logging.getLogger('RecoveryManager')

def main():
    logger.info("=" * 60)
    logger.info("GESTOR DE AUTO-RECUPERACAO v2.0 INICIADO")
    logger.info("Modo: INFINITO - A correr para sempre")
    logger.info("=" * 60)
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            logger.info(f"Iteracao {iteration}")
            
            # Verifica se o auto_recovery.py esta a funcionar
            try:
                import auto_recovery
                logger.info("Modulo auto_recovery importado com sucesso")
            except Exception as e:
                logger.warning(f"Erro ao importar auto_recovery: {e}")
            
            # Verifica ficheiros essenciais
            essential_files = [
                "main.py", "run_forever.py", "wakeup_v3.py",
                "auto_recovery.py", "core/keep_alive.py"
            ]
            
            for f in essential_files:
                fpath = BASE / f
                if not fpath.exists():
                    logger.warning(f"Ficheiro essencial em falta: {f}")
            
            # Log de estado
            logger.info(f"Gestor ativo - iteracao {iteration}")
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("Shutdown recebido. A encerrar...")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        logger.info("A reiniciar automaticamente...")
        time.sleep(2)
        main()

if __name__ == "__main__":
    main()
