from pathlib import Path

target = Path(r"C:\Users\Crypto Bull\Desktop\Agente Local\api\server.py")
content = target.read_text(encoding="utf-8")

replacements = [
    ('if path == "/health":',                    'if path in ("/health", "/api/health"):'),
    ('elif path == "/agents":',                  'elif path in ("/agents", "/api/agents"):'),
    ('elif path.startswith("/agents/")',          'elif path.startswith("/agents/") or path.startswith("/api/agents/")'),
    ('elif path == "/tasks":',                   'elif path in ("/tasks", "/api/tasks"):'),
    ('elif path == "/metrics":',                 'elif path in ("/metrics", "/api/metrics"):'),
    ('elif path == "/memory":',                  'elif path in ("/memory", "/api/memory"):'),
    ('elif path == "/audit":',                   'elif path in ("/audit", "/api/audit"):'),
    ('if path == "/agents":',                    'if path in ("/agents", "/api/agents"):'),
    ('elif path == "/shutdown":',                'elif path in ("/shutdown", "/api/shutdown"):'),
]

changed = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"  OK  {old}")
        changed += 1
    else:
        print(f"  --  nao encontrado: {old}")

target.write_text(content, encoding="utf-8")
print(f"\n{changed} substituicao(oes) feita(s). Reinicia o sistema.")