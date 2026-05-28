"""
Supervisor Agent - Núcleo do ecossistema Correoto
Orquestra todos os agentes, decide prioridades, executa evolução
"""
import json
import os
import subprocess
from datetime import datetime

class Supervisor:
    def __init__(self):
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.agents_file = os.path.join(self.root, "agents.json")
        self.log_file = os.path.join(self.root, "evolution_log.json")
        self.priorities_file = os.path.join(self.root, "priorities.json")
        self.agents = self._load_agents()
        self.logs = self._load_logs()
        self.priorities = self._load_priorities()

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
        return True

    def get_next_task(self):
        """Devolve a tarefa com maior prioridade que ainda não foi executada"""
        if not self.priorities:
            return None
        sorted_priorities = sorted(self.priorities, key=lambda x: x["weight"], reverse=True)
        return sorted_priorities[0]

    def execute_command(self, command):
        """Executa um comando shell e retorna o resultado"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=self.root)
            self.log("comando_executado", command[:50])
            return result.stdout, result.stderr
        except Exception as e:
            self.log("erro_comando", str(e))
            return "", str(e)

    def git_push(self, message):
        """Faz git add, commit e push"""
        stdout, stderr = self.execute_command("git add .")
        stdout, stderr = self.execute_command(f'git commit -m "{message}"')
        if "nothing to commit" in stdout or "nothing to commit" in stderr:
            self.log("git_sem_mudancas", "Nada para commitar")
            return False
        stdout, stderr = self.execute_command("git push")
        if "error" in stderr.lower():
            self.log("erro_git_push", stderr[:100])
            return False
        self.log("git_push", message)
        return True

    def create_file(self, path, content):
        """Cria ou substitui um ficheiro"""
        full_path = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        self.log("ficheiro_criado", path)
        return True

    def read_file(self, path):
        """Lê um ficheiro"""
        full_path = os.path.join(self.root, path)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                return f.read()
        return None

    def list_files(self, path=""):
        """Lista ficheiros de um diretório"""
        full_path = os.path.join(self.root, path)
        if os.path.exists(full_path):
            return os.listdir(full_path)
        return []

    def status_report(self):
        """Gera relatório de estado do sistema"""
        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_agents": len(self.agents),
            "active_agents": len([a for a in self.agents if a.get("status") == "active"]),
            "total_evolutions": len(self.logs),
            "priorities": self.priorities,
            "agents": self.agents[-5:]  # Últimos 5 agentes
        }
        return report


if __name__ == "__main__":
    sv = Supervisor()
    print(json.dumps(sv.status_report(), indent=2))
