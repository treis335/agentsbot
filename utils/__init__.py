"""
utils/__init__.py — Utilitarios seguros para o ecossistema Correoto.
"""

import sys


def safe_print(*args, sep=" ", end="\n", file=None):
    """
    Print seguro que nunca causa UnicodeEncodeError.
    Substitui caracteres problematicos por '?' em vez de crashar.
    """
    if file is None:
        file = sys.stdout
    
    # Tentar reconfigurar stdout para utf-8
    try:
        file.reconfigure(encoding='utf-8', errors='replace')
    except (ValueError, AttributeError):
        pass
    
    text = sep.join(str(a) for a in args) + end
    
    try:
        file.write(text)
        file.flush()
    except UnicodeEncodeError:
        # Fallback: substituir caracteres nao-ASCII
        safe_text = text.encode('utf-8', errors='replace').decode('utf-8')
        # Ainda pode falhar se o terminal for CP1252
        try:
            file.write(safe_text)
            file.flush()
        except UnicodeEncodeError:
            # Ultimo recurso: ASCII puro
            ascii_text = safe_text.encode('ascii', errors='replace').decode('ascii')
            file.write(ascii_text)
            file.flush()


def safe_log(filepath: str, msg: str):
    """Escreve no ficheiro de log de forma segura (UTF-8 sempre)."""
    import os
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line)
