"""
Evolution Engine — Motor de evolução autónoma do ecossistema Correoto
Gera novos agentes, diagnostica issues, faz auto-commit
"""
import json, os, subprocess, datetime, sys
from pathlib import Path

BASE_DIR = Path("C:/Users/Crypto Bull/Desktop/Agente Local")
AGENTS_FILE = BASE_DIR / "agents.json"
MEMORY_DIR = BASE_DIR / "memory"
EVOLUTION_FILE = MEMORY_DIR / "evolution_log.json"

class EvolutionEngine:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def carregar_agentes(self):
        with open(AGENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def salvar_agentes(self, agents):
        with open(AGENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(agents, f, indent=2, ensure_ascii=False)

    def log_evolucao(self, entry):
        logs = []
        if EVOLUTION_FILE.exists():
            with open(EVOLUTION_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        logs.append(entry)
        with open(EVOLUTION_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def diagnosticar_issues(self, agents):
        issues = []
        for a in agents:
            if a.get("status") != "active":
                issues.append(f"{a['name']}: status {a['status']}")
            if "role" not in a or not a["role"]:
                issues.append(f"{a['name']}: sem role")
        return issues

    def gerar_novo_agente(self, agents):
        novos = {
            "Analyst": {"role": "Analisador de metricas", "status": "active"},
            "Optimizer": {"role": "Otimizador de desempenho", "status": "active"},
            "Tester": {"role": "Testador automatico", "status": "active"},
            "DocsAgent": {"role": "Documentador", "status": "active"},
            "SecurityAgent": {"role": "Seguranca do sistema", "status": "active"}
        }
        for nome, dados in novos.items():
            if not any(a["name"] == nome for a in agents):
                agents.append({"name": nome, **dados})
                self.log_evolucao({"tipo": "novo_agente", "agente": nome, "data": str(datetime.datetime.now())})
                return nome
        return None

    def auto_commit(self):
        try:
            subprocess.run(["git", "add", "-A"], cwd=BASE_DIR, capture_output=True)
            msg = f"Auto-evolucao ciclo {datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            r = subprocess.run(["git", "commit", "-m", msg], cwd=BASE_DIR, capture_output=True, text=True)
            out = r.stdout + r.stderr
            if "nothing to commit" not in out:
                subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True)
                self.log_evolucao({"tipo": "git_push", "msg": msg, "data": str(datetime.datetime.now())})
                return True
        except:
            pass
        return False

    def run_evolution_cycle(self):
        agents = self.carregar_agentes()
        issues = self.diagnosticar_issues(agents)
        novo = self.gerar_novo_agente(agents)
        if novo:
            self.salvar_agentes(agents)
        commit_feito = self.auto_commit()
        return {"agentes": len(agents), "issues": len(issues), "novo_agente": novo, "commit_feito": commit_feito}

if __name__ == "__main__":
    engine = EvolutionEngine()
    resultado = engine.run_evolution_cycle()
    print(json.dumps(resultado, indent=2))
