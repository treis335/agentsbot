"""
evolution_engine.py — Motor de evolução autónoma
Cria agentes, diagnostica, faz git push, gere o ecossistema
Corre 24/7 sem intervenção
"""
import json, os, subprocess, datetime, time, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
AGENTS_FILE = BASE_DIR / "agents.json"
MEMORY_DIR = BASE_DIR / "memory"
EVOLUTION_LOG = MEMORY_DIR / "evolution_log.json"
CICLO_FILE = MEMORY_DIR / "ciclo_count.txt"

NOVOS_AGENTES = [
    ("Analyst", "Analisador de métricas e desempenho"),
    ("Optimizer", "Otimizador de código e recursos"),
    ("Tester", "Testador automático de funcionalidades"),
    ("DocsAgent", "Documentador automático do sistema"),
    ("SecurityAgent", "Segurança e permissões do sistema"),
    ("MonitorAgent", "Monitorização 24/7 de saúde do sistema"),
    ("LoggerAgent", "Gestor centralizado de logs"),
    ("BridgeAgent", "Ponte entre sandbox e ambiente local"),
    ("DeployAgent", "Gestor de deploys automáticos"),
    ("SoulAgent", "Curador de almas e personalidades"),
]

class EvolutionEngine:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    
    def carregar_agentes(self):
        with open(AGENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def salvar_agentes(self, agents):
        with open(AGENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(agents, f, indent=2, ensure_ascii=False)
    
    def log_evolucao(self, tipo, detalhe):
        logs = []
        if EVOLUTION_LOG.exists():
            with open(EVOLUTION_LOG, "r", encoding="utf-8") as f:
                logs = json.load(f)
        logs.append({
            "tipo": tipo,
            "detalhe": detalhe,
            "data": str(datetime.datetime.now())
        })
        with open(EVOLUTION_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    
    def diagnosticar(self, agents):
        issues = []
        for a in agents:
            if a.get("status") != "active":
                issues.append(f"{a['name']}: status={a.get('status')}")
            if not a.get("role"):
                issues.append(f"{a['name']}: sem role definida")
        return issues
    
    def criar_novo_agente(self, agents):
        for nome, role in NOVOS_AGENTES:
            if not any(a["name"] == nome for a in agents):
                agents.append({
                    "name": nome,
                    "role": role,
                    "status": "active",
                    "created": str(datetime.datetime.now())
                })
                self.salvar_agentes(agents)
                self.log_evolucao("novo_agente", nome)
                return nome
        return None
    
    def git_auto(self):
        try:
            subprocess.run(["git", "add", "-A"], cwd=BASE_DIR, capture_output=True)
            r = subprocess.run(
                ["git", "commit", "-m", f"Auto-evolucao {datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"],
                cwd=BASE_DIR, capture_output=True, text=True
            )
            if "nothing to commit" not in r.stdout and "nothing to commit" not in r.stderr:
                subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True)
                self.log_evolucao("git_push", "Push automático feito")
                return True
        except Exception as e:
            self.log_evolucao("erro_git", str(e))
        return False
    
    def run_evolution_cycle(self):
        agents = self.carregar_agentes()
        issues = self.diagnosticar(agents)
        novo = self.criar_novo_agente(agents)
        
        count = 0
        if CICLO_FILE.exists():
            count = int(CICLO_FILE.read_text().strip() or "0")
        count += 1
        CICLO_FILE.write_text(str(count))
        
        commit = False
        if count % 3 == 0:
            commit = self.git_auto()
        
        return {
            "agentes": len(agents),
            "issues": len(issues),
            "novo_agente": novo,
            "commit": commit,
            "ciclo": count
        }
