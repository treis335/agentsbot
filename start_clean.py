"""
start_clean.py — Inicializador seguro do ecossistema Correoto
Resolve:
1. UnicodeEncodeError (força UTF-8 no stdout/stderr ANTES de qualquer import)
2. Telegram Conflict (instance lock com kill de processos órfãos)
3. Loop infinito wakeup (mata wakeup.py primeiro)

Uso: python start_clean.py
"""
import os
import sys
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).parent.resolve()
LOCK_FILE = BASE / ".instance.lock"

def force_utf8():
    """Força UTF-8 no stdout/stderr antes de qualquer coisa."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    # Fallback: variável de ambiente
    os.environ["PYTHONIOENCODING"] = "utf-8:replace"

def kill_all_python_instances(except_pid=None):
    """Mata todas as instâncias python excepto a atual."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if "python.exe" not in line:
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                pid_str = parts[1].strip().strip('"')
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if except_pid is not None and pid == except_pid:
                        continue
                    try:
                        os.kill(pid, 9)
                        print(f"  [KILL] Processo python PID {pid} morto")
                    except (OSError, PermissionError):
                        pass
    except Exception as e:
        print(f"  [AVISO] Erro ao matar processos: {e}")

def cleanup_lock():
    """Remove lock file se existir."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        print("  [LOCK] Ficheiro .instance.lock removido")

def create_lock():
    """Cria lock file com o PID atual."""
    LOCK_FILE.write_text(str(os.getpid()))
    print(f"  [LOCK] Criado .instance.lock (PID {os.getpid()})")

def main():
    print("=" * 60)
    print("  CORREOTO — Inicializador Seguro v1.0")
    print("=" * 60)
    
    # 1. Forçar UTF-8
    print("\n[1/5] A forçar UTF-8 no stdout/stderr...")
    force_utf8()
    
    # 2. Matar todas as outras instâncias python
    print("\n[2/5] A limpar processos python órfãos...")
    kill_all_python_instances(except_pid=os.getpid())
    time.sleep(1)
    
    # 3. Limpar lock file antigo
    print("\n[3/5] A limpar lock files...")
    cleanup_lock()
    
    # 4. Criar novo lock
    print("\n[4/5] A criar novo lock...")
    create_lock()
    
    # 5. Iniciar main.py
    print("\n[5/5] A iniciar main.py...")
    print("-" * 60)
    
    # Usar PYTHONIOENCODING para garantir UTF-8
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8:replace"
    
    proc = subprocess.Popen(
        [sys.executable, str(BASE / "main.py")],
        cwd=str(BASE),
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print(f"  [OK] main.py iniciado (PID {proc.pid})")
    print(f"  [OK] A correr em nova consola")
    print("=" * 60)
    
    # Não bloquear — o main.py corre na sua própria consola
    return 0

if __name__ == "__main__":
    sys.exit(main())
