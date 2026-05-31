#!/usr/bin/env python3
"""Limpar ultima tarefa running."""
import json
b = json.load(open('memory/backlog.json', 'r', encoding='utf-8'))
for t in b:
    if t.get('status') == 'running':
        print(f'ID={t.get("id")} title={str(t.get("title","?"))[:60]}')
        t['status'] = 'failed'
        t['completed_at'] = '2026-05-31T02:10:00'
        t['result'] = 'Auto-fix: tarefa running presa'
json.dump(b, open('memory/backlog.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
b2 = json.load(open('memory/backlog.json', 'r', encoding='utf-8'))
s = {}
for t in b2:
    st = t.get('status', '?')
    s[st] = s.get(st, 0) + 1
print(f'Final: {s}')
print(f'Running: {sum(1 for t in b2 if t.get("status")=="running")}')
