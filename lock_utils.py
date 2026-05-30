"""
lock_utils.py — Utilitário de lock de instância única.

Garante que apenas uma instância do processo corre de cada vez,
usando um ficheiro de lock com o PID do processo.
"""
import os
import sys
import time
import logging

logger = logging.getLogger(__name__)

LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".correoto.lock")


def acquire_lock(timeout: int = 5) -> bool:
    """
    Tenta adquirir o lock de processo.
    Retorna True se conseguiu, False se já existe outra instância.
    """
    # Se o lock já existe, verificar se o processo ainda está vivo
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            # Verificar se o PID ainda existe
            if _pid_alive(old_pid):
                logger.warning(f"[Lock] Processo {old_pid} j? est? a correr.")
                return False
            else:
                # PID morto — lock obsoleto, remover
                logger.info(f"[Lock] Lock obsoleto do PID {old_pid}. A limpar...")
                os.remove(LOCK_FILE)
        except (ValueError, OSError):
            # Ficheiro corrompido ou removido entretanto
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass

    # Criar o lock com o PID actual
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"[Lock] Lock adquirido (PID {os.getpid()})")
        return True
    except OSError as e:
        logger.error(f"[Lock] N?o foi poss?vel criar lock: {e}")
        return False


def release_lock() -> None:
    """Liberta o lock de processo."""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(LOCK_FILE)
                logger.info("[Lock] Lock libertado.")
    except (ValueError, OSError) as e:
        logger.warning(f"[Lock] Erro ao libertar lock: {e}")


def _pid_alive(pid: int) -> bool:
    """Verifica se um PID está vivo (cross-platform)."""
    if sys.platform == "win32":
        import ctypes
        PROCESS_QUERY_INFORMATION = 0x0400
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
        if handle == 0:
            return False
        exit_code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return exit_code.value == 259  # STILL_ACTIVE
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False