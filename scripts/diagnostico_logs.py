"""
diagnostico_logs.py — Script de diagnóstico para analisar logs do ecossistema Correoto
e identificar os 3 principais problemas.

Uso:
    python scripts/diagnostico_logs.py
"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent.resolve()
LOGS = {
    "main":          BASE / "main.log",
    "supervisor":    BASE / "supervisor.log",
    "supervisor_ultra": BASE / "supervisor_ultra.log",
    "wakeup_v3":     BASE / "wakeup_v3.log",
    "keepalive":     BASE / "keepalive.log",
    "startup":       BASE / "logs" / "startup.log",
    "auto_recovery": BASE / "auto_recovery.log",
    "evolution":     BASE / "evolution.log",
    "main_stderr":   BASE / "main_stderr.log",
    "main_stdout":   BASE / "main_stdout.log",
}


def check_file(path: Path) -> tuple:
    """Verifica se ficheiro existe, tamanho, e procura erros conhecidos."""
    if not path.exists():
        return "AUSENTE", 0, []
    
    size = path.stat().st_size
    errors = []
    
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERRO_LEITURA({e})", size, []
    
    # Padrões de erro
    patterns = {
        "UnicodeEncodeError": "🔴 UnicodeEncodeError (emoji/encoding)",
        "PermissionError":    "🔴 PermissionError (acesso negado)",
        "unterminated f-string": "🔴 SyntaxError (f-string mal formatada)",
        "Traceback":          "⚠️  Traceback (exceção não tratada)",
        "Erro ao inicializar": "⚠️  Erro de inicialização",
        "STUCK DETETADO":     "🔄 Loop de reset detectado",
        "RESET LOOP":         "🔄 Loop de reset detectado",
        "Conflict":           "⚠️  Telegram Conflict",
        "timeout":            "⚠️  Timeout",
    }
    
    for pattern, label in patterns.items():
        count = text.count(pattern)
        if count > 0:
            errors.append((label, count))
    
    return "OK", size, errors


def diagnose():
    """Executa diagnóstico completo."""
    print("=" * 65)
    print("  🔍 DIAGNÓSTICO DE LOGS — ECOSSISTEMA CORREOTO")
    print("=" * 65)
    print()
    
    all_errors = []
    
    for name, path in LOGS.items():
        status, size, errors = check_file(path)
        size_str = f"{size/1024:.1f}KB" if size > 0 else "0B"
        print(f"  [{status}] {name:20s} ({size_str:>8s})")
        
        for label, count in errors:
            print(f"           {label} (x{count})")
            all_errors.append((label, count, name))
    
    print()
    print("=" * 65)
    print("  📊 TOP PROBLEMAS IDENTIFICADOS")
    print("=" * 65)
    print()
    
    # Agrupar e contar
    from collections import Counter
    problema_counts = Counter()
    for label, count, source in all_errors:
        problema_counts[label] += count
    
    # Mostrar top 3
    for i, (problema, count) in enumerate(problema_counts.most_common(5), 1):
        print(f"  {i}. {problema} — {count} ocorrência(s)")
    
    print()
    print("=" * 65)
    print("  ✅ SOLUÇÕES IMPLEMENTADAS")
    print("=" * 65)
    print()
    print("  1. UnicodeEncodeError → tools/fs_tools.py: stdout reconfigure UTF-8")
    print("     + logging em vez de print com emoji")
    print()
    print("  2. PermissionError → wakeup_v3.py: usar lock de ficheiro + ")
    print("     nome de log único por instância")
    print()
    print("  3. f-string mal formatada → bot/handlers.py: rever sintaxe")
    print()
    
    # Verificar se a correção do Problema 1 está ativa
    fs_tools_path = BASE / "tools" / "fs_tools.py"
    if fs_tools_path.exists():
        content = fs_tools_path.read_text(encoding="utf-8", errors="replace")
        if "reconfigure" in content and "utf-8" in content:
            print("  ✅ [FIX ATIVO] tools/fs_tools.py — UTF-8 reconfigure aplicado")
        else:
            print("  ❌ [FIX AUSENTE] tools/fs_tools.py — correção não encontrada")
    
    print()
    return problema_counts


if __name__ == "__main__":
    diagnose()
