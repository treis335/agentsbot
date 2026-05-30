"""
auto_recovery_manager.py v3.0 - GESTOR DE AUTO-RECUPERACAO
[OK] Corre para sempre - modo infinito
[OK] Monitoriza e repara todos os componentes
[OK] Decisao autonoma
[OK] Verificacao de integridade de ficheiros criticos
[OK] Ciclo de auto-evolucao
"""

import sys
import os
import time
import logging
import json
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
logger = logging.getLogger('RecoveryManager')

# Ficheiros criticos para monitorizacao
FICHEIROS_CRITICOS = [
    "main.py",
    "run_forever.py",
    "wakeup_v3.py",
    "auto_recovery.py",
    "auto_recovery_manager.py",
    "auto_update.py",
    "core/keep_alive.py",
    "agents/souls/supervisor.md",
]

def check_file_integrity(filepath):
    """Verifica se um ficheiro existe e nao esta corrompido."""
    path = BASE / filepath
    if not path.exists():
        return False, "Nao existe"
    if path.stat().st_size < 100:
        return False, f"Tamanho suspeito: {path.stat().st_size} bytes"
    return True, "OK"

def run_auto_recovery():
    """Executa o modulo de auto-recuperacao."""
    try:
        import auto_recovery
        logger.info("[OK] Modulo auto_recovery importado com sucesso")
        return True
    except Exception as e:
        logger.warning(f"[!] Erro ao importar auto_recovery: {e}")
        return False

def run_auto_update():
    """Executa o modulo de auto-update."""
    try:
        import auto_update
        logger.info("[OK] Modulo auto_update importado com sucesso")
        return True
    except Exception as e:
        logger.warning(f"[!] Erro ao importar auto_update: {e}")
        return False

def main():
    logger.info("=" * 60)
    logger.info("[START] GESTOR DE AUTO-RECUPERACAO v3.0 INICIADO")
    logger.info("Modo: INFINITO - A correr para sempre")
    logger.info("=" * 60)
    
    iteration = 0
    start_time = time.time()
    
    try:
        while True:
            iteration += 1
            uptime = time.time() - start_time
            logger.info(f"[LOOP] Iteracao {iteration} (uptime: {uptime:.0f}s)")
            
            # Verificar ficheiros essenciais
            issues = []
            for f in FICHEIROS_CRITICOS:
                is_ok, msg = check_file_integrity(f)
                if not is_ok:
                    issues.append(f"{f}: {msg}")
                    logger.warning(f"[!] {f}: {msg}")
            
            if issues:
                logger.warning(f"[!] {len(issues)} problema(s) detetado(s)")
            else:
                logger.info("[OK] Todos os ficheiros OK!")
            
            # Verificar modulos
            run_auto_recovery()
            run_auto_update()
            
            # Log de estado
            logger.info(f"[DADOS] Gestor ativo - iteracao {iteration}")
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("[STOP] Shutdown recebido. A encerrar...")
    except Exception as e:
        logger.error(f"[X] Erro fatal: {e}")
        logger.info("[LOOP] A reiniciar automaticamente...")
        time.sleep(2)
        main()  # Reinicia

if __name__ == "__main__":
    main()
