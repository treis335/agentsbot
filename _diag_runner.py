#!/usr/bin/env python3
"""Diagnóstico rápido do sistema."""
import json
from datetime import datetime

# 1. Backlog
b = json.load(open('memory/backlog.json', 'r', encoding='utf-8'))
print(f'=== BACKLOG ===')
print(f'Total: {len(b)}')
status = {}
for t in b:
    s = t.get('status', '?')
    status[s] = status.get(s, 0) + 1
print(f'Status: {status}')

print('\n=== RUNNING (potencialmente presas) ===')
now = datetime.now()
for t in b:
    if t.get('status') == 'running':
        created = t.get('created', 'unknown')
        print(f'  [{created}] {t.get("id","?")}: {t.get("title","?")[:80]}')

print('\n=== FAILED ===')
for t in b:
    if t.get('status') == 'failed':
        created = t.get('created', 'unknown')
        print(f'  [{created}] {t.get("id","?")}: {t.get("title","?")[:80]}')

print('\n=== PENDING ===')
for t in sorted(b, key=lambda x: x.get('priority', 99)):
    if t.get('status') == 'pending':
        print(f'  P{t.get("priority",5)}: {t.get("title","?")[:80]}')

# 2. Verificar ficheiros .lock
import os
try:
    locks = [f for f in os.listdir('.') if f.endswith('.lock')]
    print(f'\n=== LOCKS ===')
    print(f'Ficheiros .lock: {locks}')
except:
    print('Erro ao listar locks')

# 3. Verificar __pycache__
import glob
pyc = glob.glob('**/__pycache__/**', recursive=True)
print(f'\n=== PYCACHE ===')
print(f'Ficheiros em __pycache__: {len(pyc)}')

# 4. Verificar git status
print('\n=== GIT ===')
import subprocess
r = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f'Ficheiros alterados: {len(lines)}')
for line in lines:
    print(f'  {line}')
