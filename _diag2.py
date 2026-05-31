#!/usr/bin/env python3
"""Diagnóstico aprofundado do bug do OrganicMind."""
import json
import sys
sys.path.insert(0, '.')

# 1. Verificar o backlog atual
b = json.load(open('memory/backlog.json', 'r', encoding='utf-8'))
print(f'=== BACKLOG: {len(b)} tarefas ===')

# Contar por status
from collections import Counter
status_count = Counter(t.get('status', '?') for t in b)
print(f'Status: {dict(status_count)}')

# 2. Verificar se há tarefas sem 'title'
no_title = [t for t in b if 'title' not in t and 'desc' not in t]
print(f'\nTarefas sem title nem desc: {len(no_title)}')
for t in no_title[:5]:
    print(f'  ID={t.get("id","?")} keys={list(t.keys())}')

# 3. Verificar tarefas 'running' há muito tempo
from datetime import datetime
now = datetime.now()
for t in b:
    if t.get('status') == 'running':
        created = t.get('created_at') or t.get('created', '')
        if created:
            try:
                dt = datetime.fromisoformat(created)
                hours = (now - dt).total_seconds() / 3600
                print(f'\nRUNNING há {hours:.1f}h: {t.get("id","?")} - {t.get("title","?")[:60]}')
            except:
                print(f'\nRUNNING (data inválida): {t.get("id","?")}')

# 4. Simular o erro 'title' no OrganicMind
# O erro acontece quando collective_debate retorna algo sem a chave esperada
# ou quando _call_llm_simple falha silenciosamente
print('\n=== ANÁLISE DO BUG OrganicMind ===')
print('''
O erro "KeyError: 'title'" acontece porque:
1. OrganicMind.collective_debate() chama _call_llm_simple()
2. _call_llm_simple() chama _call_llm() que precisa de DEEPSEEK_API_KEY
3. Se a API key nao existe ou a API falha, levanta excecao
4. A excecao nao e tratada com fallback -> KeyError no autonomous_loop.py
''')

# 5. Verificar se a env tem DEEPSEEK_API_KEY
import os
from pathlib import Path
env_path = Path('.env')
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if 'DEEPSEEK' in line or 'API_KEY' in line:
            print(f'ENV: {line[:30]}...')
else:
    print('ENV: .env nao encontrado!')
