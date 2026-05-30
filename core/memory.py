"""
core/memory.py - Memoria persistente do ecossistema Correoto
Guarda interacoes, contexto e estado para o sistema nao alucinar.

NOTA: Esta implementacao agora delega no MemoryHub (core/memory_hub.py)
para unificar os 3 sistemas de memoria. A API publica mantem-se igual.
"""

import json
import os
from datetime import datetime

from core.memory_hub import MemoryHub

MEMORY_DIR = "memory"
CONV_FILE = os.path.join(MEMORY_DIR, "conversation.jsonl")
STATE_FILE = os.path.join(MEMORY_DIR, "state.json")


class ConversationMemory:
    """Memoria de conversa persistente em ficheiro JSONL.
    
    Wrapper para MemoryHub — mantem a API original para compatibilidade.
    Os dados sao armazenados no MemoryHub (hub.jsonl).
    """
    
    def __init__(self):
        self._hub = MemoryHub()
        os.makedirs(MEMORY_DIR, exist_ok=True)
    
    def add(self, role, content, metadata=None):
        """Adiciona uma interacao a memoria."""
        return self._hub.store_chat(role, content, metadata)
    
    def get_recent(self, n=10):
        """Devolve as ultimas N interacoes."""
        chats = self._hub.get_chats(limit=n)
        return [c["data"] for c in chats]
    
    def get_all(self):
        """Devolve todas as interacoes."""
        entries = self._hub._read_all()
        return [e["data"] for e in entries if e.get("type") == "chat"]
    
    def get_context(self, n=5):
        """Devolve contexto formatado para o LLM (ultimas N interacoes)."""
        return self._hub.get_context(n=n)
    
    def clear(self):
        """Limpa a memoria (uso em desenvolvimento)."""
        self._hub.clear()
        return True


class SystemState:
    """Estado persistente do sistema (nao se perde com reboots).
    
    NOTA: Este continua a usar state.json para nao quebrar compatibilidade.
    """
    
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.state = self._load()
    
    def _load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                return {}
        return {}
    
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
