#!/usr/bin/env python3
"""Script para atualizar agents/executor.py - substituir memória antiga por MemoryHub."""
import sys

BASE = r'C:\Users\Crypto Bull\Desktop\Agente Local'

with open(BASE + r'\agents\executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = list(lines)

# === REPLACEMENT 1: GlobalMemory in _build_memory_context (lines 139-156) ===
repl1 = [
    '        # Mem\xc3\xb3ria global partilhada (via MemoryHub)\n',
    '        try:\n',
    '            decisions = self.memory.get_decisions(limit=5)\n',
    '            if decisions:\n',
    '                lines.append("\\n### Decis\xc3\xb5es da Equipa (mem\xc3\xb3ria global)")\n',
    '                for d in decisions:\n',
    '                    lines.append(f"  [{d[\'timestamp\'][:16]}] {d[\'agent\']}: {d[\'decision\'][:80]}")\n',
    '\n',
    '            knowledge = self.memory.get_knowledge(limit=5)\n',
    '            if knowledge:\n',
    '                lines.append("\\n### Conhecimento Partilhado")\n',
    '                for k in knowledge:\n',
    '                    lines.append(f"  {k[\'data\'][\'topic\']}: {k[\'data\'][\'content\'][:80]}")\n',
    '        except Exception as e:\n',
    '            logger.debug(f"[{self.agent_name}] Mem\xc3\xb3ria global indispon\xc3\xadvel: {e}")\n',
]
new_lines[138:156] = repl1

# === REPLACEMENT 2: LessonExtractor ===
repl2 = [
    '        # Li\xc3\xa7\xc3\xb5es aprendidas (via MemoryHub)\n',
    '        try:\n',
    '            lessons = self.memory.get_lessons(agent_id=self.agent_id, limit=4)\n',
    '            if lessons:\n',
    '                lines.append("\\n### Li\xc3\xa7\xc3\xb5es Aprendidas (evita estes erros)")\n',
    '                for lesson in lessons:\n',
    '                    lines.append(f"  {lesson}")\n',
    '        except Exception as e:\n',
    '            logger.debug(f"[{self.agent_name}] Li\xc3\xa7\xc3\xb5es indispon\xc3\xadveis: {e}")\n',
]
new_lines[156:165] = repl2

# === REPLACEMENT 3: ProceduralMemory ===
repl3 = [
    '        # Procedimentos HOW-TO relevantes (via MemoryHub)\n',
    '        try:\n',
    '            procs = self.memory.get_procedural(task, limit=2)\n',
    '            if procs:\n',
    '                proc_ctx = "\\n### Procedimentos Relacionados\\n"\n',
    '                for p in procs:\n',
    '                    proc_ctx += f"  - {p[\'data\'][\'content\'][:200]}\\n"\n',
    '        except Exception as e:\n',
    '            logger.debug(f"[{self.agent_name}] Procedimentos indisponiveis: {e}")\n',
]
new_lines[191:199] = repl3

# === REPLACEMENT 4: FailureMemory ===
repl4 = [
    '        # Falhas similares (via MemoryHub)\n',
    '        try:\n',
    '            failures = self.memory.get_failures(agent_id=self.agent_id, limit=2)\n',
    '            if failures:\n',
    '                failure_ctx = "\\n### Falhas Recentes (evita repetir)\\n"\n',
    '                for f in failures:\n',
    '                    action = f[\'data\'].get("action", f[\'data\'].get("task", "?"))\n',
    '                    result = f[\'data\'].get("result", "")[:80]\n',
    '                    failure_ctx += f"  - {action}: {result}\\n"\n',
    '        except Exception as e:\n',
    '            logger.debug(f"[{self.agent_name}] Failure memory indisponivel: {e}")\n',
]
new_lines[203:211] = repl4

# === REPLACEMENT 5: GlobalMemory.add_decision ===
repl5 = [
    '                # Registar na mem\xc3\xb3ria global (via MemoryHub)\n',
    '                try:\n',
    '                    self.memory.add_decision(\n',
    '                        agent    = self.agent_name,\n',
    '                        decision = f"Completou: {task[:80]}",\n',
    '                        context  = (msg.content or "")[:200],\n',
    '                    )\n',
    '                except Exception:\n',
    '                    pass\n',
]
new_lines[327:335] = repl5

# Write back
with open(BASE + r'\agents\executor.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Ficheiro atualizado com sucesso!")

# Verify
content = ''.join(new_lines)
checks = [
    'from memory.global_memory import GlobalMemory',
    'from memory.lesson_extractor import LessonExtractor',
    'from memory.procedural import ProceduralMemory',
    'from memory.failure_memory import FailureMemory',
]
for c in checks:
    print(f"  {c}: {'ENCONTRADO (ERRO!)' if c in content else 'removido OK'}")

print(f"\nTotal lines: {len(new_lines)}")
