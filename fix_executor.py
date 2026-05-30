#!/usr/bin/env python3
"""Script to update executor.py to use MemoryHub instead of direct memory imports."""
import sys
sys.path.insert(0, '.')

with open('agents/executor.py', 'r', encoding='utf-8', errors='replace') as f:
    exec = f.read()

# 1. Replace ProceduralMemory in build_system_prompt
old_proc = '''        proc_ctx = ""
        try:
            from memory.procedural import ProceduralMemory
            proc_mem = ProceduralMemory()
            relevant_procs = proc_mem.get_relevant(task, limit=2)
            if relevant_procs:
                proc_ctx = "\\n" + proc_mem.format_for_prompt(relevant_procs)
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Procedimentos indisponiveis: {e}")'''

new_proc = '''        proc_ctx = ""
        try:
            relevant_procs = self.memory.get_procedural(task, limit=2)
            if relevant_procs:
                proc_lines = ["\\n### Procedimentos Relevantes"]
                for p in relevant_procs:
                    proc_lines.append(f"  - {p['data']['content'][:100]}")
                proc_ctx = "\\n".join(proc_lines)
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Procedimentos indisponiveis: {e}")'''

if old_proc in exec:
    exec = exec.replace(old_proc, new_proc)
    print("[OK] ProceduralMemory -> MemoryHub")
else:
    print("[WARN] ProceduralMemory pattern not found exactly")

# 2. Replace FailureMemory in build_system_prompt
old_fail = '''        failure_ctx = ""
        try:
            from memory.failure_memory import FailureMemory
            fm = FailureMemory(self.agent_id)
            similar = fm.get_similar_failures(task, limit=2)
            if similar:
                failure_ctx = "\\n" + fm.format_for_prompt(similar)
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Failure memory indisponivel: {e}")'''

new_fail = '''        failure_ctx = ""
        try:
            failures = self.memory.get_episodes(self.agent_id, limit=2, only_failures=True)
            if failures:
                fail_lines = ["\\n### Falhas Similares (evita repetir)"]
                for ep in failures:
                    d = ep["data"]
                    action = d.get("action", d.get("task", "?"))
                    result = d.get("result", "")[:60]
                    fail_lines.append(f"  [FAIL] {action} -> {result}")
                failure_ctx = "\\n".join(fail_lines)
        except Exception as e:
            logger.debug(f"[{self.agent_name}] Failure memory indisponivel: {e}")'''

if old_fail in exec:
    exec = exec.replace(old_fail, new_fail)
    print("[OK] FailureMemory -> MemoryHub")
else:
    print("[WARN] FailureMemory pattern not found exactly")

# 3. Replace GlobalMemory().add_decision in execute method
old_decision = '''                    from memory.global_memory import GlobalMemory
                    GlobalMemory().add_decision(
                        agent    = self.agent_name,
                        decision = f"Completou: {task[:80]}",
                        context  = (msg.content or "")
                    )'''

new_decision = '''                    self.memory.add_decision(
                        agent    = self.agent_name,
                        decision = f"Completou: {task[:80]}",
                        context  = (msg.content or "")
                    )'''

if old_decision in exec:
    exec = exec.replace(old_decision, new_decision)
    print("[OK] GlobalMemory().add_decision -> MemoryHub.add_decision")
else:
    print("[WARN] GlobalMemory().add_decision pattern not found exactly")

# Check remaining direct imports
import re
remaining = re.findall(r'from memory\.\w+ import \w+', exec)
if remaining:
    print(f"\n[WARN] Remaining direct memory imports: {remaining}")
else:
    print("\n[OK] No remaining direct memory imports from memory/")

with open('agents/executor.py', 'w', encoding='utf-8') as f:
    f.write(exec)

print("\nDone updating executor.py!")
