"""
Supervisor Agent - Núcleo do ecossistema Correoto
Orquestra todos os agentes, decide prioridades, executa evolução
Com memória de conversa persistente integrada.
"""
import json
import os
import subprocess
from datetime import datetime

# Importar memória de conversa
from core.memory_hub import MemoryHub, get_memory_hub

class Supervisor:
    def __init__(self):
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.agents_file = os.path.join(self.root, "agents.json")
        self.log_file = os.path.join(self.root, "evolution_log.json")
        self.priorities_file = os.path.join(self.root, "priorities.json")
        self.agents = self._load_agents()
        self.logs = self._load_logs()
        self.priorities = self._load_priorities()
        # Memória de conversa
        self.memory = MemoryHub()

    def _load_agents(self):
        if os.path.exists(self.agents_file):
            with open(self.agents_file, "r") as f:
                return json.load(f)
        return []

    def _load_logs(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as f:
                return json.load(f)
        return []

    def _load_priorities(self):
        if os.path.exists(self.priorities_file):
            with open(self.priorities_file, "r") as f:
                return json.load(f)
        return []

    def _save_agents(self):
        with open(self.agents_file, "w") as f:
            json.dump(self.agents, f, indent=2)

    def _save_logs(self):
        with open(self.log_file, "w") as f:
            json.dump(self.logs, f, indent=2)

    def _save_priorities(self):
        with open(self.priorities_file, "w") as f:
            json.dump(self.priorities, f, indent=2)

    def log(self, tipo, detalhe):
        entry = {
            "tipo": tipo,
            "detalhe": detalhe,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.logs.append(entry)
        self._save_logs()
        print(f"[SUPERVISOR] {tipo}: {detalhe}")

    def remember(self, speaker: str, message: str):
        """Guarda uma interação na memória de conversa."""
        context = {
            "agents_count": len(self.agents),
            "logs_count": len(self.logs),
            "priorities_count": len(self.priorities)
        }
        self.memory.remember(speaker, message, context)

    def get_context(self) -> str:
        """Devolve o contexto da conversa para o Supervisor não se repetir."""
        return self.memory.summary()

    def get_last_human_message(self) -> str:
        """Devolve a última mensagem do humano."""
        return self.memory.last_human_message() or ""

    def get_last_supervisor_message(self) -> str:
        """Devolve a última mensagem do Supervisor."""
        return self.memory.last_supervisor_message() or ""

    def add_agent(self, name, mission, file_path):
        # Verificar se já existe
        for a in self.agents:
            if a["name"] == name:
                return False
        agent = {
            "name": name,
            "mission": mission,
            "file": file_path,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"
        }
        self.agents.append(agent)
        self._save_agents()
        self.log("novo_agente", name)
        self.remember("supervisor", f"Criei o agente {name} com missão: {mission}")
        return True

    def update_priority(self, task, weight):
        for p in self.priorities:
            if p["task"] == task:
                p["weight"] = weight
                self._save_priorities()
                self.log("prioridade_atualizada", f"{task}: {weight}")
                return True
        self.priorities.append({"task": task, "weight": weight})
        self._save_priorities()
        self.log("nova_prioridade", f"{task}: {weight}")
        self.remember("supervisor", f"Nova prioridade: {task} (peso {weight})")
        return True

    def get_next_task(self):
        """Devolve a tarefa com maior prioridade que ainda não foi executada"""
        if not self.priorities:
            return None
        # Ordenar por peso (maior primeiro)
        sorted_p = sorted(self.priorities, key=lambda x: x.get("weight", 0), reverse=True)
        return sorted_p[0] if sorted_p else None

    def get_status(self) -> dict:
        """Devolve o estado atual do ecossistema."""
        return {
            "agents": len(self.agents),
            "logs": len(self.logs),
            "priorities": len(self.priorities),
            "conversation_history": self.memory.count_human_messages(),
            "last_human": self.get_last_human_message()[:100] if self.get_last_human_message() else None,
            "last_supervisor": self.get_last_supervisor_message()[:100] if self.get_last_supervisor_message() else None,
            "timestamp": datetime.now().isoformat()
        }

    def run(self):
        """Ciclo principal do Supervisor."""
        self.log("ciclo", "Supervisor a executar ciclo principal")
        context = self.get_context()
        print(f"[SUPERVISOR] Contexto da conversa:\n{context[:500]}")
        return context


# Instância global
supervisor = Supervisor()
