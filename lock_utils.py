"""
lock_utils.py — Mecanismo de lock singleton para o ecossistema CORREOTO

Garante que apenas uma instância do bot Telegram/main.py corre de cada vez.
Usa um ficheiro .lock com PID para detectar instâncias concorrentes.

Uso:
    from lock_utils import acquire_lock, release_lock, LOCK_FILE
    if not acquire_lock():
        sys.exit("Outra instância já está a correr. A encerrar.")
    try:
        ...  # teu código
    finally:
        release_lock()
"""
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger("correoto.lock")

# Caminho do ficheiro de lock — partilhado entre main.py e wakeup_v3.py
LOCK_FILE = Path(__file__).parent / "bot_telegram.lock"


def _pid_is_alive(pid: int) -> bool:
    """Verifica se um PID ainda está ativo no sistema (cross-platform)."""
    try:
        if sys.platform == "win32":
            import subprocess
            result = subprocess.run(
                f'tasklist /FI "PID eq {pid}" /FO CSV /NH',
                capture_output=True, text=True, shell=True, timeout=5
            )
            return str(pid) in result.stdout
        else:
            # Linux / macOS
            os.kill(pid, 0)  # signal 0 = testa se o processo existe
            return True
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False
    except Exception:
        return False


def acquire_lock() -> bool:
    """
    Tenta adquirir o lock singleton.
    Returns True se conseguiu (ou lock era órfão e foi limpo).
    Returns False se outra instância válida está a correr.
    """
    lock_path = LOCK_FILE

    if lock_path.exists():
        try:
            raw = lock_path.read_text(encoding="utf-8").strip()
            if raw:
                pid = int(raw)
                if pid != os.getpid() and _pid_is_alive(pid):
                    logger.warning(
                        "[Lock] Outra instância já está a correr (PID %d). A encerrar.",
                        pid,
                    )
                    return False
                elif pid == os.getpid():
                    # Já somos nós — lock válido
                    return True
        except (ValueError, OSError, Exception):
            pass

        # Lock órfão — remover
        try:
            lock_path.unlink()
            logger.info("[Lock] Lock órfão removido.")
        except Exception:
            pass

    # Criar novo lock
    try:
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
        logger.info("[Lock] Lock adquirido (PID %d).", os.getpid())
        return True
    except Exception as e:
        logger.error("[Lock] Erro ao criar lock: %s", e)
        return False


def release_lock() -> None:
    """Liberta o lock se formos os donos."""
    lock_path = LOCK_FILE
    try:
        if lock_path.exists():
            raw = lock_path.read_text(encoding="utf-8").strip()
            if raw and int(raw) == os.getpid():
                lock_path.unlink()
                logger.info("[Lock] Lock libertado (PID %d).", os.getpid())
    except (ValueError, OSError, Exception):
        pass
