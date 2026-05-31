"""
diagnostico_rapido.py — Diagnóstico rápido do ecossistema Correoto
===================================================================
Analisa logs e estado actual, reporta problemas conhecidos.

Uso:
    python scripts/diagnostico_rapido.py
"""

# ============================================================
# FIX: Forcar UTF-8 no stdout/stderr para evitar UnicodeEncodeError
# com emojis no Windows (CP1252)
# ============================================================
import sys
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

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent

def check_processos():
    """Verifica processos Python e main.py"""
    print("\n🔍 PROCESSOS:")
    if os.name == "nt":
        result = subprocess.run('tasklist /FO CSV | findstr /i python', 
                              shell=True, capture_output=True, text=True)
        lines = [l for l in result.stdout.strip().split('\n') if l]
        print(f"  Processos Python: {len(lines)}")
        for l in lines:
            parts = l.split(',')
            if len(parts) >= 2:
                pid = parts[1].strip('"')
                name = parts[0].strip('"')
                # Ver se é main.py
                cmd = subprocess.run(f'wmic process where processid={pid} get commandline /FORMAT:VALUE',
                                   shell=True, capture_output=True, text=True)
                if 'main.py' in cmd.stdout:
                    print(f"  ⚠️  PID {pid} — MAIN.PY ATIVO")
                elif 'run_forever' in cmd.stdout:
                    print(f"  ⚠️  PID {pid} — RUN_FOREVER ATIVO")
    else:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'main.py' in line:
                print(f"  ⚠️  {line.strip()[:100]}")

def check_logs():
    """Verifica tamanho dos logs"""
    print("\n📊 LOGS:")
    total = 0
    for f in BASE.glob("*.log"):
        sz = f.stat().st_size
        total += sz
        status = "⚠️  GRANDE" if sz > 5*1024*1024 else "✅ OK"
        print(f"  {status} {f.name}: {sz/1024/1024:.1f} MB")
    print(f"  Total: {total/1024/1024:.1f} MB")

def check_locks():
    """Verifica locks"""
    print("\n🔒 LOCKS:")
    for lf in BASE.glob("*.lock"):
        try:
            content = lf.read_text(encoding="utf-8", errors="replace").strip()
            pid = None
            try:
                data = json.loads(content)
                pid = data.get("pid")
            except:
                pid = int(content)
            
            # Verificar processo
            if os.name == "nt":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x0400, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    print(f"  ✅ {lf.name} — PID {pid} (ativo)")
                else:
                    print(f"  ⚠️  {lf.name} — PID {pid} (MORTO!)")
            else:
                try:
                    os.kill(pid, 0)
                    print(f"  ✅ {lf.name} — PID {pid} (ativo)")
                except:
                    print(f"  ⚠️  {lf.name} — PID {pid} (MORTO!)")
        except:
            print(f"  ⚠️  {lf.name} — (não lido)")

def check_erros_recentes():
    """Verifica erros recentes no main.log"""
    print("\n🚨 ÚLTIMOS ERROS (main.log):")
    log_file = BASE / "main.log"
    if not log_file.exists():
        print("  ❌ main.log não encontrado")
        return
    
    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    # Contar tipos de erro
    from collections import Counter
    erros = Counter()
    for line in lines[-5000:]:  # últimas 5000 linhas
        if 'Conflict: terminated' in line:
            erros['Telegram Conflict'] += 1
        elif 'UnicodeEncodeError' in line:
            erros['UnicodeEncodeError'] += 1
        elif 'timeout' in line.lower() and 'error' in line.lower():
            erros['Timeout'] += 1
        elif 'connection' in line.lower() and 'error' in line.lower():
            erros['Connection Error'] += 1
    
    for erro, count in erros.most_common(5):
        print(f"  {count:>5}x {erro}")

def main():
    print("=" * 60)
    print(f"🔍 DIAGNÓSTICO RÁPIDO — CORREOTO ECOSYSTEM")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    check_processos()
    check_logs()
    check_locks()
    check_erros_recentes()
    
    print("\n" + "=" * 60)
    print("✅ Diagnóstico concluído")
    print("=" * 60)

if __name__ == "__main__":
    main()
