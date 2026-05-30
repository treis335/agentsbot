with open('agents/executor.py', 'r', encoding='utf-8') as f:
    content = f.read()
with open('agents/executor.py', 'w', encoding='utf-8') as f:
    # Substituir GlobalMemory por MemoryHub
    content = content.replace(
        "from memory.global_memory import GlobalMemory\n            gm = GlobalMemory()\n\n            decisions = gm.get_decisions(5)",
        "hub = MemoryHub()\n            decisions = hub.get_decisions()"
    )
    content = content.replace(
        "from memory.lesson_extractor import LessonExtractor\n            lessons = LessonExtractor().get_lessons_for_agent(self.agent_id, limit=4)",
        "hub = MemoryHub()\n            lessons = hub.get_lessons()"
    )
    content = content.replace(
        "from memory.global_memory import GlobalMemory\n                    GlobalMemory().add_decision(",
        "MemoryHub().add_decision("
    )
    f.write(content)
print("Substituições feitas.")
