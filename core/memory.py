"""
core/memory.py - Memoria persistente do ecossistema Correoto
Guarda interacoes, contexto e estado para o sistema nao alucinar.
"""

import json
import os
from datetime import datetime

MEMORY_DIR = "memory"
CONV_FILE = os.path.join(MEMORY_DIR, "conversation.jsonl")
STATE_FILE = os.path.join(MEMORY_DIR, "state.json")

class ConversationMemory:
    """Memoria de conversa persistente em ficheiro JSONL."""
    
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        if not os.path.exists(CONV_FILE):
            with open(CONV_FILE, 'w', encoding='utf-8') as f:
                f.write("")
    
    def add(self, role, content, metadata=None):
        """Adiciona uma interacao a memoria."""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        with open(CONV_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry
    
    def get_recent(self, n=10):
        """Devolve as ultimas N interacoes."""
        if not os.path.exists(CONV_FILE):
            return []
        with open(CONV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line.strip()))
            except:
                pass
        return entries
    
    def get_all(self):
        """Devolve todas as interacoes."""
        if not os.path.exists(CONV_FILE):
            return []
        with open(CONV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        entries = []
        for line in lines:
            try:
                entries.append(json.loads(line.strip()))
            except:
                pass
        return entries
    
    def get_context(self, n=5):
        """Devolve contexto formatado para o LLM (ultimas N interacoes)."""
        recent = self.get_recent(n)
        if not recent:
            return "Sem historico de conversa."
        context = "Historico recente:\n"
        for entry in recent:
            role = entry.get('role', '?')
            content = entry.get('content', '')[:200]
            context += f"[{role}] {content}\n"
        return context
    
    def clear(self):
        """Limpa a memoria (uso em desenvolvimento)."""
        with open(CONV_FILE, 'w', encoding='utf-8') as f:
            f.write("")
        return True

class SystemState:
    """Estado persistente do sistema (nao se perde com reboots)."""
    
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.state = self._load()
    
    def _load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "boot_count": 0,
            "last_boot": None,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "current_task": None,
            "last_evolution": None,
            "last_git_push": None
        }
    
    def _save(self):
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def get(self, key, default=None):
        return self.state.get(key, default)
    
    def set(self, key, value):
        self.state[key] = value
        self._save()
    
    def increment(self, key):
        self.state[key] = self.state.get(key, 0) + 1
        self._save()
    
    def record_boot(self):
        self.state["boot_count"] = self.state.get("boot_count", 0) + 1
        self.state["last_boot"] = datetime.now().isoformat()
        self._save()
    
    def record_task_completed(self):
        self.state["tasks_completed"] = self.state.get("tasks_completed", 0) + 1
        self._save()
    
    def record_task_failed(self):
        self.state["tasks_failed"] = self.state.get("tasks_failed", 0) + 1
        self._save()
