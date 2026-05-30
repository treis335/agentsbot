import re

with open('agents/executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1) Substituir bloco GlobalMemory (linhas ~139-156)
# Antes:
#         # Memória global partilhada
#         try:
#             from memory.global_memory import GlobalMemory
#             gm = GlobalMemory()
#             decisions = gm.get_decisions(5)
#             if decisions:
#                 lines.append(...)
#                 for d in decisions:
#                     ...
#         except Exception as e:
#             logger.debug(...)
old_block1 = """        # Mem\u00f3ria global partilhada
        try:
            from memory.global_memory import GlobalMemory
            gm = GlobalMemory()

            decisions = gm.get_decisions(5)
            if decisions:
                lines.append("\\n### Decis\u00f5es da Equipa (mem\u00f3ria global)")
                for d in decisions:
                    agent = d.get("agent", "desconhecido")
                    decision = d.get("decision", "")
                    context = d.get("context", "")
                    lines.append(f"- [{agent}] {decision} | contexto: {context[:100]}")
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Mem\u00f3ria global indispon\u00edvel: {e}")"""

new_block1 = """        # Mem\u00f3ria global partilhada (via MemoryHub)
        try:
            decisions = self.memory.get_decisions(5)
            if decisions:
                lines.append("\\n### Decis\u00f5es da Equipa (mem\u00f3ria global)")
                for d in decisions:
                    agent = d.get("agent", "desconhecido")
                    decision = d.get("decision", "")
                    context = d.get("context", "")
                    lines.append(f"- [{agent}] {decision} | contexto: {context[:100]}")
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Mem\u00f3ria global indispon\u00edvel: {e}")"""

if old_block1 in content:
    content = content.replace(old_block1, new_block1)
    print("OK: Substituiu bloco GlobalMemory (decisions)")
else:
    print("AVISO: Bloco GlobalMemory (decisions) nao encontrado exatamente")
    # Tentar encontrar versão aproximada
    if 'from memory.global_memory import GlobalMemory' in content:
        print("  -> 'GlobalMemory' ainda presente no ficheiro")
    if 'gm.get_decisions' in content:
        print("  -> 'gm.get_decisions' ainda presente")

# 2) Substituir bloco LessonExtractor (linhas ~158-166)
old_block2 = """                # Li\u00e7\u00f5es aprendidas (Batch 4)
        try:
            from memory.lesson_extractor import LessonExtractor
            lessons = LessonExtractor().get_lessons_for_agent(self.agent_id, limit=4)
            if lessons:
                lines.append("\\n### Li\u00e7\u00f5es Aprendidas (evita estes erros)")
                for lesson in lessons:
                    lines.append(f"\u26a1 {lesson}")
        except Exception as e:
            logger.debug(f"[{self.agent_name}] LessonExtractor indispon\u00edvel: {e}")"""

new_block2 = """                # Li\u00e7\u00f5es aprendidas (via MemoryHub)
        try:
            lessons = self.memory.get_lessons(limit=4)
            if lessons:
                lines.append("\\n### Li\u00e7\u00f5es Aprendidas (evita estes erros)")
                for lesson in lessons:
                    lines.append(f"\u26a1 {lesson}")
        except Exception as e:
            logger.debug(f"[{self.agent_name}] MemoryHub.get_lessons indispon\u00edvel: {e}")"""

if old_block2 in content:
    content = content.replace(old_block2, new_block2)
    print("OK: Substituiu bloco LessonExtractor")
else:
    print("AVISO: Bloco LessonExtractor nao encontrado exatamente")
    if 'LessonExtractor' in content:
        print("  -> 'LessonExtractor' ainda presente no ficheiro")

# 3) Substituir bloco GlobalMemory add_decision (linhas ~325-332)
old_block3 = """                # Registar na mem\u00f3ria global
                try:
                    from memory.global_memory import GlobalMemory
                    GlobalMemory().add_decision(
                        agent    = self.agent_name,
                        decision = f"Completou: {task[:80]}",
                        context  = (msg.content or "")[:200],
                    )"""

new_block3 = """                # Registar na mem\u00f3ria global (via MemoryHub)
                try:
                    self.memory.add_decision(
                        agent    = self.agent_name,
                        decision = f"Completou: {task[:80]}",
                        context  = (msg.content or "")[:200],
                    )"""

if old_block3 in content:
    content = content.replace(old_block3, new_block3)
    print("OK: Substituiu bloco GlobalMemory add_decision")
else:
    print("AVISO: Bloco GlobalMemory add_decision nao encontrado exatamente")
    if 'GlobalMemory().add_decision' in content:
        print("  -> 'GlobalMemory().add_decision' ainda presente")

with open('agents/executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerificacao final:")
if 'GlobalMemory' in content:
    print("AVISO: Ainda ha referencias a GlobalMemory")
else:
    print("OK: Nenhuma referencia a GlobalMemory")

if 'LessonExtractor' in content:
    print("AVISO: Ainda ha referencias a LessonExtractor")
else:
    print("OK: Nenhuma referencia a LessonExtractor")
