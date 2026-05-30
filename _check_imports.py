import re

for fname in ['core/supervisor.py', 'agents/executor.py']:
    print(f'--- {fname} ---')
    with open(fname, 'r', encoding='utf-8') as f:
        c = f.read()
    imports = re.findall(r'^from .* import.*$|^import .*$', c, re.MULTILINE)
    for i in imports:
        print(i)
    print()
    if 'memory_hub' in c:
        print('OK: usa memory_hub')
    if 'ConversationMemory' in c:
        print('AVISO: ainda usa ConversationMemory')
    if 'MemoryHub' in c:
        print('OK: usa MemoryHub')
    if 'EpisodicMemory' in c:
        print('AVISO: ainda usa EpisodicMemory')
    if 'GlobalMemory' in c:
        print('AVISO: ainda usa GlobalMemory')
    print()
