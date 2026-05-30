"""
telegram_lock.py — Lock seguro para o bot Telegram
===================================================
Garante que apenas UMA instância do bot faz polling ao Telegram.
Usa um ficheiro .lock + verificação de processo real.

Problema resolvido:
    Telegram ConflictError — "terminated by other getUpdates request"
    acontecia porque wakeup_v3.py, heartbeat_system.py e supervisor_ultra.py
    reiniciavam o main.py múltiplas vezes, criando N instâncias a competir.

Uso:
    from telegram_lock import acquire_telegram_lock, release_telegram_lock
    if not acquire_telegram_lock():
        sys.exit(0)  # já há outra instância
"""

import os
import sys
import json
import time
import socket
import subprocess
from pathlib import Path

LOCK_FILE = Path(__file__).parent / ".telegram.lock"


def acquire_telegram_lock() -> bool:
    """
    Tenta adquirir o lock do Telegram.
    Retorna True se conseguiu (é o dono), False se já há outro dono ativo.
    """
    if LOCK_FILE.exists():
        try:
            data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            pid = data.get("pid", 0)
            hostname = data.get("hostname", "")
            timestamp = data.get("timestamp", "")

            if _is_process_alive(pid):
                print(
                    f"[TelegramLock] Outra instância ativa "
                    f"(PID {pid}, desde {timestamp}). A sair."
                )
                return False
            else:
                print(
                    f"[TelegramLock] Lock expirado (PID {pid} já não existe). "
                    f"A reclamar..."
                )
        except (json.JSONDecodeError, OSError):
            print("[TelegramLock] Ficheiro de lock corrompido. A reclamar...")

    try:
        data = {
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": time.time(),
        }
        LOCK_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[TelegramLock] Lock adquirido (PID {os.getpid()}).")
        return True
    except OSError as e:
        print(f"[TelegramLock] ERRO ao criar lock: {e}")
        return True  # fail-open


def release_telegram_lock():
    """Liberta o lock do Telegram (apenas se formos o dono)."""
    if not LOCK_FILE.exists():
        return
    try:
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        if data.get("pid") == os.getpid():
            LOCK_FILE.unlink()
            print(f"[TelegramLock] Lock libertado (PID {os.getpid()}).")
    except (json.JSONDecodeError, OSError):
        pass


def _is_process_alive(pid: int) -> bool:
    """Verifica se um processo com o PID dado ainda existe (cross-platform)."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def force_release_lock():
    """Força a libertação do lock (usar em caso de emergência)."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        print("[TelegramLock] Lock libertado à força.")


if __name__ == "__main__":
    if acquire_telegram_lock():
        print("[TelegramLock] Lock adquirido com sucesso!")
        print("Prima Ctrl+C para libertar...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            release_telegram_lock()
            print("[TelegramLock] Lock libertado.")
    else:
        print("[TelegramLock] Não foi possível adquirir o lock.")
        sys.exit(1)
