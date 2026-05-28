import json, os, subprocess, datetime, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
AGENTS_FILE = BASE_DIR / "agents.json"
MEMORY_DIR = BASE_DIR / "memory"
EVOLUTION_FILE = MEMORY_DIR / "evolution_log.json"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def carregar_agentes():
    with open(AGENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_agentes(agents):
    with open(AGENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2, ensure_ascii=False)

def log_evolucao(entry):
    logs = []
    if EVOLUTION_FILE.exists():
        with open(EVOLUTION_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    logs.append(entry)
    with open(EVOLUTION_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

def diagnosticar_issues(agents):
    issues = []
    for a in agents:
        if a.get("status") != "active":
            issues.append(f"{a['name']}: status {a['status']}")
        if "role" not in a or not a["role"]:
            issues.append(f"{a['name']}: sem role")
    return issues

def gerar_novo_agente(agents):
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
            log_evolucao({"tipo": "novo_agente", "agente": nome, "data": str(datetime.datetime.now())})
            return nome
    return None

def auto_commit():
    try:
        subprocess.run(["git", "add", "-A"], cwd=BASE_DIR, capture_output=True)
        msg = f"Auto-evolucao ciclo {datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        r = subprocess.run(["git", "commit", "-m", msg], cwd=BASE_DIR, capture_output=True, text=True)
        if "nothing to commit" not in r.stdout and "nothing to commit" not in r.stderr:
            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, capture_output=True)
            log_evolucao({"tipo": "git_push", "msg": msg, "data": str(datetime.datetime.now())})
            return True
    except:
        pass
    return False

def run_evolution():
    agents = carregar_agentes()
    issues = diagnosticar_issues(agents)
    novo = gerar_novo_agente(agents)
    if novo:
        salvar_agentes(agents)
    commit_feito = auto_commit()
    return {"agentes": len(agents), "issues": len(issues), "novo_agente": novo, "commit_feito": commit_feito}

if __name__ == "__main__":
    resultado = run_evolution()
    print(json.dumps(resultado, indent=2))
