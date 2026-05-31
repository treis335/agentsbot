"""
health_check.py — Verificação rápida de saúde do ecossistema Correoto
Corre diagnostics e reporta problemas conhecidos.

Uso: python health_check.py
"""
import os
import sys
import subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

def check_fix_encoding():
    """Verifica se o fix_encoding está operacional."""
    path = os.path.join(BASE, "fix_encoding.py")
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✅ fix_encoding.py ({size} bytes)")
        return True
    else:
        print(f"  ❌ fix_encoding.py NÃO ENCONTRADO!")
        return False

def check_wakeup_crash_loop():
    """Verifica se a função _check_crash_loop existe no wakeup.py."""
    path = os.path.join(BASE, "wakeup.py")
    if not os.path.exists(path):
        print(f"  ❌ wakeup.py NÃO ENCONTRADO!")
        return False
    
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    if "def _check_crash_loop" in content:
        print(f"  ✅ wakeup.py: _check_crash_loop() implementada")
        return True
    else:
        print(f"  ❌ wakeup.py: _check_crash_loop() AUSENTE!")
        return False

def check_log_sizes():
    """Verifica tamanhos de logs para detetar crescimento anormal."""
    logs = [
        ("wakeup_v3.log", 500_000),
        ("wakeup.log", 100_000),
        ("supervisor.log", 10_000),
    ]
    
    all_ok = True
    for log_name, max_size in logs:
        path = os.path.join(BASE, log_name)
        if os.path.exists(path):
            size = os.path.getsize(path)
            status = "⚠️" if size > max_size else "✅"
            print(f"  {status} {log_name}: {size:,} bytes {'(GRANDE!)' if size > max_size else ''}")
            if size > max_size:
                all_ok = False
        else:
            print(f"  ⚪ {log_name}: não encontrado")
    
    return all_ok

def check_python_version():
    """Verifica versão do Python."""
    v = sys.version_info
    print(f"  ✅ Python {v.major}.{v.minor}.{v.micro}")
    return v.major >= 3 and v.minor >= 10

def check_env_file():
    """Verifica se .env existe e tem token."""
    path = os.path.join(BASE, ".env")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "TELEGRAM_TOKEN" in content and "=" in content:
            print(f"  ✅ .env encontrado com TELEGRAM_TOKEN")
            return True
        else:
            print(f"  ⚠️ .env encontrado mas sem TELEGRAM_TOKEN")
            return False
    else:
        print(f"  ⚠️ .env NÃO ENCONTRADO")
        return False

def main():
    print("=" * 60)
    print(f"  HEALTH CHECK — CORREOTO ECOSYSTEM")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Path: {BASE}")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("fix_encoding.py", check_fix_encoding),
        ("Crash Loop Protection", check_wakeup_crash_loop),
        ("Log Sizes", check_log_sizes),
        ("Environment", check_env_file),
    ]
    
    results = []
    for name, func in checks:
        print(f"\n[{name}]")
        try:
            result = func()
            results.append(result)
        except Exception as e:
            print(f"  ❌ ERRO: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    ok = sum(1 for r in results if r)
    total = len(results)
    print(f"  RESULTADO: {ok}/{total} checks OK")
    
    if ok < total:
        print("  ⚠️ Existem problemas para resolver.")
    else:
        print("  ✅ Sistema saudável!")
    print("=" * 60)

if __name__ == "__main__":
    main()
