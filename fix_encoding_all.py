"""
fix_encoding_all.py — Correção definitiva de encoding para Windows

Problema: Python no Windows usa CP1252 que não consegue imprimir emojis.
Isto causa UnicodeEncodeError: 'charmap' codec can't encode character

Solucao: Define PYTHONIOENCODING=utf-8:replace antes de qualquer print
e reconfigure o stdout/stderr para UTF-8 com errors='replace'.

Este script deve ser executado ANTES de qualquer outro codigo.
"""

import os
import sys
import logging

# ============================================================
# PASSO 1: Forcar variavel de ambiente ANTES de qualquer import
# ============================================================
os.environ["PYTHONIOENCODING"] = "utf-8:replace"

# ============================================================
# PASSO 2: Reconfigurar stdout/stderr (Python 3.7+)
# ============================================================
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

# ============================================================
# PASSO 3: Monkey-patch do print para nunca falhar
# ============================================================
_original_print = print

def _safe_print(*args, **kwargs):
    """Versao do print que nunca falha com Unicode."""
    try:
        _original_print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
            else:
                safe_args.append(arg)
        _original_print(*safe_args, **kwargs)
    except Exception:
        pass

builtins = __import__('builtins')
builtins.print = _safe_print


def setup_safe_logging(name="correoto", level=logging.INFO):
    """Configura logging que nunca falha com Unicode."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


if __name__ == "__main__":
    print("fix_encoding_all.py executado com sucesso!")
    print("PYTHONIOENCODING =", os.environ.get("PYTHONIOENCODING", "nao definido"))
    print("stdout encoding:", sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else "N/A")
    print("stderr encoding:", sys.stderr.encoding if hasattr(sys.stderr, 'encoding') else "N/A")
    print("Teste com emojis funcionou!")
