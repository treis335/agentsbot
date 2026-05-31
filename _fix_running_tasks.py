#!/usr/bin/env python3
"""Correção 1: Limpar tarefas 'running' presas há mais de 30min."""
import json
from datetime import datetime

b = json.load(open('memory/backlog.json', 'r', encoding='utf-8'))
now = datetime.now()
fixes = 0

for t in b:
    if t.get('status') == 'running':
        created = t.get('created_at') or t.get('created', '')
        if created:
            try:
                dt = datetime.fromisoformat(created)
                mins = (now - dt).total_seconds() / 60
                if mins > 30:
                    print(f'[FIX] running -> failed: {t.get("id","?")} ({mins:.0f}min) - {str(t.get("title","?"))[:60]}')
                    t['status'] = 'failed'
                    t['completed_at'] = now.isoformat()
                    t['result'] = 'Auto-fix: tarefa presa em running >30min'
                    fixes += 1
            except:
                print(f'[FIX] running -> failed (data invalida): {t.get("id","?")}')
                t['status'] = 'failed'
                t['completed_at'] = now.isoformat()
                t['result'] = 'Auto-fix: tarefa presa em running (data invalida)'
                fixes += 1

if fixes > 0:
    json.dump(b, open('memory/backlog.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n✅ {fixes} tarefas running presas movidas para failed')
else:
    print('Nenhuma tarefa running presa encontrada')
