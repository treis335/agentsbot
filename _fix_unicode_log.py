#!/usr/bin/env python3
"""
Correção 3: Prevenir UnicodeEncodeError no log do autonomous_loop.py.
O Windows usa cp1252 que nao suporta emojis. A funcao log_cycle ja tenta
mas o supervisor_ultra.py crashou com UnicodeEncodeError.
Vamos tornar a funcao log_cycle bulletproof.
"""
with open('autonomous_loop.py', 'r', encoding='utf-8') as f:
    content = f.read()

# A funcao log_cycle atual:
old_log = '''def log_cycle(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (ValueError, AttributeError):
        pass
    try:
        print(line)
    except UnicodeEncodeError:
        safe_line = line.encode('utf-8', errors='replace').decode('utf-8')
        print(safe_line)
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\\n")'''

new_log = '''def log_cycle(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Sanitizar: substituir caracteres que o Windows cp1252 nao suporta
    safe_msg = msg.encode('utf-8', errors='replace').decode('utf-8')
    line = f"[{timestamp}] {safe_msg}"
    # Tentar forcar utf-8 no stdout (funciona em alguns Windows)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (ValueError, AttributeError):
        pass
    try:
        print(line)
    except UnicodeEncodeError:
        # Fallback: remover tudo que nao seja ASCII
        ascii_line = line.encode('ascii', errors='replace').decode('ascii')
        print(ascii_line)
    except Exception:
        # Ultimo recurso: print basico
        print(f"[{timestamp}] [log]")
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\\n")'''

if old_log in content:
    content = content.replace(old_log, new_log)
    print('✅ log_cycle atualizado com protecao Unicode')
else:
    print('⚠️  Funcao log_cycle original nao encontrada')
    # Tentar encontrar
    if 'def log_cycle' in content:
        print('  def log_cycle encontrada - possivelmente ja modificada')

with open('autonomous_loop.py', 'w', encoding='utf-8') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print('✅ Sintaxe OK')
except SyntaxError as e:
    print(f'❌ Erro de sintaxe: {e}')
