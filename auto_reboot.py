"""
auto_reboot.py — Auto-Reboot Inteligente

Quando o sistema deteta que houve alteracoes ao codigo fonte,
cria um ficheiro sinalizador (auto_reboot.flag) e reinicia-se
automaticamente para aplicar as mudancas sem intervencao humana.

Uso:
    from auto_reboot import trigger_reboot, check_reboot_flag
    
    # Para agendar reboot:
    trigger_reboot("Memoria de conversa adicionada")
    
    # No main.py, ao arrancar:
    check_reboot_flag()
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REBOOT_FLAG = Path("auto_reboot.flag")
REBOOT_LOG = Path("memory") / "reboot_history.json"

def trigger_reboot(reason: str = "Atualizacao de codigo"):
    """
    Cria o sinalizador de reboot e reinicia o processo.
    O main.py deve ler este sinalizador ao arrancar.
    """
    # Guardar motivo do reboot
    MemoryDir = Path("memory")
    MemoryDir.mkdir(exist_ok=True)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "pid": os.getpid()
    }
    
    # Guardar historico de reboots
    history = []
    if REBOOT_LOG.exists():
        try:
            with open(REBOOT_LOG, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            pass
    
    history.append(entry)
    
    with open(REBOOT_LOG, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    # Criar sinalizador
    with open(REBOOT_FLAG, "w", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, indent=2))
    
    logger.info(f"[AutoReboot] Sinalizador criado: {reason}")
    
    # Reiniciar o processo
    logger.info(f"[AutoReboot] A reiniciar o sistema...")
    time.sleep(1)
    os.execv(sys.executable, [sys.executable, "main.py"])

def check_reboot_flag():
    """
    Verifica se existe sinalizador de reboot.
    Se sim, regista e limpa.
    Deve ser chamado no inicio do main.py.
    """
    if REBOOT_FLAG.exists():
        try:
            with open(REBOOT_FLAG, "r", encoding="utf-8") as f:
                data = json.load(f)
            reason = data.get("reason", "Desconhecido")
            logger.info(f"[AutoReboot] Sistema reiniciado apos: {reason}")
            print(f"[AUTO-REBOOT] Sistema reiniciado apos: {reason}")
        except:
            print("[AUTO-REBOOT] Sistema reiniciado (sinalizador encontrado)")
        
        # Limpar sinalizador
        REBOOT_FLAG.unlink(missing_ok=True)
        return True
    return False

def get_reboot_history() -> list:
    """Devolve o historico de reboots."""
    if REBOOT_LOG.exists():
        try:
            with open(REBOOT_LOG, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

if __name__ == "__main__":
    # Teste: verificar se ha sinalizador
    if check_reboot_flag():
        print("Sinalizador de reboot encontrado e limpo.")
    else:
        print("Nenhum sinalizador de reboot encontrado.")
    
    print(f"Historico de reboots: {len(get_reboot_history())}")
