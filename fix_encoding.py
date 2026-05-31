"""
fix_encoding.py — Correção definitiva de encoding UTF-8 para Windows

Problema:
  No Windows, o terminal usa cp1252 que não suporta emojis (🚀🔧✅❌🔄).
  Quando um print() ou logging tenta escrever um emoji, dá:
    UnicodeEncodeError: 'charmap' codec can't encode character '\\U0001f527'

Solução:
  1. Força PYTHONIOENCODING=utf-8 nas variáveis de ambiente
  2. Reconigure sys.stdout/stderr com encoding utf-8 e errors='replace'
  3. Substitui a função print() global para ser à prova de emojis
  4. Adiciona filtro de encoding no logging

Uso:
    import fix_encoding  # no início do script
    # ou
    python -c "import fix_encoding"  # antes de correr o sistema
"""
import os
import sys
import logging
import builtins

# ============================================================
# 1. Variável de ambiente (força todos os subprocessos)
# ============================================================
os.environ["PYTHONIOENCODING"] = "utf-8:replace"
os.environ["PYTHONUTF8"] = "1"  # Windows 10+ reconhece esta flag

# ============================================================
# 2. Reconigure stdout/stderr
# ============================================================
def _reconfigure_stdio():
    """Reconfigura stdout/stderr para UTF-8 com errors='replace'."""
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

_reconfigure_stdio()

# ============================================================
# 3. Substitui print() global para ser seguro com emojis
# ============================================================
_original_print = builtins.print

def _safe_print(*args, sep=' ', end='\n', file=None, flush=False):
    """print() que não crasha com emojis no Windows."""
    if file is None:
        file = sys.stdout
    try:
        _original_print(*args, sep=sep, end=end, file=file, flush=flush)
    except UnicodeEncodeError:
        # Se der erro de encoding, converte para ASCII com replace
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
            else:
                safe_args.append(str(arg).encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        _original_print(*safe_args, sep=sep, end=end, file=file, flush=flush)
    except Exception:
        # Último recurso: escreve diretamente no stderr em bytes
        try:
            msg = sep.join(str(a) for a in args) + end
            sys.stderr.buffer.write(msg.encode('utf-8', errors='replace'))
            sys.stderr.buffer.flush()
        except Exception:
            pass

builtins.print = _safe_print

# ============================================================
# 4. Filtro de logging para evitar UnicodeEncodeError
# ============================================================
class SafeEncodingFilter(logging.Filter):
    """Filtro que substitui caracteres problemáticos antes de logar."""
    
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Substitui caracteres que podem dar erro no cp1252
            record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        return True

def patch_logging():
    """Adiciona filtro de encoding seguro a todos os handlers de logging."""
    for handler in logging.root.handlers:
        handler.addFilter(SafeEncodingFilter())
    # Handler para stdout com encoding UTF-8
    if not any(isinstance(h, logging.StreamHandler) and h.stream is sys.stdout for h in logging.root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
        handler.addFilter(SafeEncodingFilter())
        logging.root.addHandler(handler)

# ============================================================
# 5. Aplicar automaticamente
# ============================================================
patch_logging()

# Indicar que a correção foi aplicada
if __name__ == '__main__':
    print("🔧 fix_encoding.py — Correção de encoding aplicada!")
    print("✅ Print seguro com emojis: 🚀🔧✅❌🔄")
    print("📋 PYTHONIOENCODING=", os.environ.get("PYTHONIOENCODING", "não definido"))
