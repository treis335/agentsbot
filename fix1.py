# -*- coding: utf-8 -*-
content = open('agents/executor.py', 'r', encoding='utf-8').read()

substituicoes = [
    (
        "from memory.global_memory import GlobalMemory\n            gm = GlobalMemory()\n\n            decisions = gm.get_decisions(5)",
        "decisions = self.memory.get_decisions(5)"
    ),
    (
        "from memory.lesson_extractor import LessonExtractor\n            lessons = LessonExtractor().get_lessons_for_agent(self.agent_id, limit=4)",
        "lessons = self.memory.get_lessons(limit=4)"
    ),
    (
        "from memory.global_memory import GlobalMemory\n                    GlobalMemory().add_decision(",
        "self.memory.add_decision("
    ),
]

for old, new in substituicoes:
    if old in content:
        content = content.replace(old, new)
        print(f"OK: Substituiu")
    else:
        print(f"AVISO: Nao encontrou -> {old[:60]}...")

open('agents/executor.py', 'w', encoding='utf-8').write(content)
print("Ficheiro escrito com sucesso!")

# Verificar
c2 = open('agents/executor.py', 'r', encoding='utf-8').read()
print(f"GlobalMemory: {'SIM' if 'GlobalMemory' in c2 else 'NAO'}")
print(f"LessonExtractor: {'SIM' if 'LessonExtractor' in c2 else 'NAO'}")
