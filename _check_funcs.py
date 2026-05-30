import re
with open('core/memory_hub.py', 'r', encoding='utf-8') as f:
    content = f.read()
funcs = re.findall(r'def \w+', content)
for f in funcs:
    print(f)
print('---')
# Ver métodos específicos
for method in ['store_chat', 'store_episode', 'store_knowledge', 'get_context', 'remember', 'summary', 'last_human_message', 'last_supervisor_message', 'clear', 'stats']:
    if f'def {method}' in content:
        print(f'OK: {method}')
    else:
        print(f'MISSING: {method}')
