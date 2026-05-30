# -*- coding: utf-8 -*-
with open('agents/executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Substituicoes usando strings literais (sem caracteres especiais problematicos)
substituicoes = [
    # 1) Bloco GlobalMemory decisions
    (
        "from memory.global_memory import GlobalMemory\n            gm = GlobalMemory()\n\n            decisions = gm.get_decisions(5)",
        "decisions = self.memory.get_decisions(5)"
    ),
    # 2) Bloco LessonExtractor
    (
        "from memory.lesson_extractor import LessonExtractor\n            lessons = LessonExtractor().get_lessons_for_agent(self.agent_id, limit=4)",
        "lessons = self.memory.get_lessons(limit=4)"
    ),
    # 3) GlobalMemory().add_decision -> self.memory.add_decision
    (
        "from memory.global_memory import GlobalMemory\n                    GlobalMemory().add_decision(",
        "self.memory.add_decision("
    ),
]

for old, new in substituicoes:
    if old in content:
        content = content.replace(old, new)
        print(f"OK: Substituiu -> {new[:50]}...")
    else:
        print(f"AVISO: Nao encontrou -> {old[:50]}...")
        # Tentar encontrar versao aproximada
        parts = old.split('\n')
        for p in parts:
            if p.strip() in content:
                print(f"  Encontrou parte: {p.strip()[:60]}")

with open('agents/executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n--- Verificacao final ---")
with open('agents/executor.py', 'r', encoding='utf-8') as f:
    c2 = f.read()

if 'GlobalMemory' in c2:
    print("AVISO: Ainda ha GlobalMemory")
else:
    print("OK: Sem GlobalMemory")

if 'LessonExtractor' in c2:
    print("AVISO: Ainda ha LessonExtractor")
else:
    print("OK: Sem LessonExtractor")

if 'gm.get_decisions' in c2:
    print("AVISO: Ainda ha gm.get_decisions")
else:
    print("OK: Sem gm.get_decisions")
