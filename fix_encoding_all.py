"""
fix_encoding_all.py — Remove caracteres nao-ASCII (emojis, acentos)
de todos os prints/logs para evitar UnicodeEncodeError no Windows cp1252.

Uso: python fix_encoding_all.py
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent

def sanitize_text(text: str) -> str:
    """Remove ou substitui caracteres fora do range ASCII basico."""
    result = []
    for ch in text:
        if ord(ch) < 128:  # ASCII puro
            result.append(ch)
        elif ch in ('\n', '\r', '\t'):
            result.append(ch)
        else:
            # Substitui emoji/unicode por equivalente ASCII ou vazio
            result.append('?')
    return ''.join(result)

def fix_file(filepath: Path) -> bool:
    """Remove caracteres nao-ASCII de strings literais num ficheiro .py."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception:
        return False

    original = content

    # 1. Remove emojis/unicode de strings literais (entre aspas)
    # Padrao: captura strings entre aspas simples/duplas/triplas
    lines = content.split('\n')
    new_lines = []
    modified = False

    for line in lines:
        # Verifica se a linha tem caracteres nao-ASCII
        has_non_ascii = any(ord(c) > 127 and c not in ('\n', '\r', '\t') for c in line)

        if has_non_ascii and ('print(' in line or 'log(' in line or 'f"' in line or "f'" in line or 'logger.' in line):
            # Sanitiza a linha inteira
            sanitized = sanitize_text(line)
            new_lines.append(sanitized)
            if sanitized != line:
                modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = '\n'.join(new_lines)
        filepath.write_text(new_content, encoding='utf-8')
        return True
    return False

def main():
    py_files = list(BASE.rglob('*.py'))
    fixed = 0
    total = 0

    for f in py_files:
        # Ignora diretorios virtuais
        if any(p.startswith('.') for p in f.parts):
            continue
        if '__pycache__' in f.parts:
            continue
        if '.venv' in f.parts or 'venv' in f.parts or '.env' in f.parts:
            continue

        total += 1
        if fix_file(f):
            print(f'[FIXED] {f.relative_to(BASE)}')
            fixed += 1

    print(f'\n=== Resumo: {fixed}/{total} ficheiros modificados ===')

if __name__ == '__main__':
    main()
