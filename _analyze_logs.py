import sys, json
from collections import Counter

data = json.load(open(r'C:\Users\Crypto Bull\Desktop\Agente Local\security\audit\audit.log', encoding='utf-8'))
erros = [x for x in data if not x.get('success')]

tipos = Counter()
for x in erros:
    r = str(x.get('result',''))
    if 'sem argumentos' in r:
        tipos['write_file sem args'] += 1
    elif 'UnicodeEncodeError' in r:
        tipos['UnicodeEncodeError'] += 1
    elif 'permission' in r.lower():
        tipos['Permissão'] += 1
    elif 'timeout' in r.lower():
        tipos['Timeout'] += 1
    elif 'not found' in r.lower() or 'não encontrado' in r.lower():
        tipos['Não encontrado'] += 1
    elif 'git' in r.lower():
        tipos['Git error'] += 1
    else:
        tipos[r[:80]] += 1

print(f"Total chamadas: {len(data)}")
print(f"Total erros: {len(erros)} ({len(erros)/len(data)*100:.1f}%)")
print()
print("Top padrões de erro:")
for t, c in tipos.most_common(10):
    print(f"  [{c}x] {t}")
