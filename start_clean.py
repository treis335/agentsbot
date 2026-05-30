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

# ============================================================
# FIX #1: Importar fix_encoding PRIMEIRO para evitar crash com emojis
# ============================================================
import fix_encoding  # noqa: F401

BASE = Path(__file__).parent.resolve()
LOCK_FILE = BASE / ".instance.lock"

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
    print("  CORREOTO — Inicializador Seguro v2.0")
    print("  🔧 Encoding UTF-8 ativo — emojis seguros! 🚀✅")
    print("=" * 60)
    
    # 1. Matar todas as outras instâncias python
    print("\n[1/5] A limpar processos python órfãos...")
    kill_all_python_instances(except_pid=os.getpid())
    time.sleep(1)
    
    # 2. Limpar lock file antigo
    print("\n[2/5] A limpar lock files...")
    cleanup_lock()
    
    # 3. Criar novo lock
    print("\n[3/5] A criar novo lock...")
    create_lock()
    
    # 4. Iniciar main.py
    print("\n[4/5] A iniciar main.py...")
    print("-" * 60)
    
    # Iniciar main.py com PYTHONIOENCODING forçado
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8:replace"
    env["PYTHONUTF8"] = "1"
    
    proc = subprocess.Popen(
        [sys.executable, str(BASE / "main.py")],
        cwd=BASE,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    print(f"  [OK] main.py iniciado (PID {proc.pid})")
    print(f"  [API] http://localhost:8080")
    print("=" * 60)
    
    # Mostrar output do main.py em tempo real
    try:
        for line in proc.stdout:
            print(line, end='', flush=True)
    except KeyboardInterrupt:
        print("\n[!] Interrompido pelo utilizador")
        proc.terminate()
    except Exception as e:
        print(f"\n[!] Erro: {e}")
        proc.terminate()

if __name__ == "__main__":
    main()
