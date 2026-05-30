# -*- coding: utf-8 -*-
path = r'C:\Users\Crypto Bull\Desktop\Agente Local\agents\executor.py'
content = open(path, 'r', encoding='utf-8').read()

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
        print(f"AVISO: Nao encontrou -> {repr(old[:80])}...")

# Escrever para novo ficheiro
new_path = r'C:\Users\Crypto Bull\Desktop\Agente Local\agents\executor_new.py'
with open(new_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Escrito para {new_path}")

# Verificar
c2 = open(new_path, 'r', encoding='utf-8').read()
print(f"GlobalMemory: {'SIM' if 'GlobalMemory' in c2 else 'NAO'}")
print(f"LessonExtractor: {'SIM' if 'LessonExtractor' in c2 else 'NAO'}")
print(f"self.memory.get_decisions: {'SIM' if 'self.memory.get_decisions' in c2 else 'NAO'}")
print(f"self.memory.get_lessons: {'SIM' if 'self.memory.get_lessons' in c2 else 'NAO'}")
print(f"self.memory.add_decision: {'SIM' if 'self.memory.add_decision' in c2 else 'NAO'}")
