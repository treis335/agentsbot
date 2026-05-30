with open('agents/executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Mostrar contexto em torno das linhas problemáticas
targets = [141, 142, 160, 161, 327, 328]
for t in targets:
    start = max(0, t-5)
    end = min(len(lines), t+5)
    print(f'--- Contexto linha {t} ---')
    for i in range(start, end):
        marker = '>>>' if i+1 == t else '   '
        print(f'{marker} {i+1}: {lines[i].rstrip()}')
    print()
