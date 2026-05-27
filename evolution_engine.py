"""
evolution_engine.py — Motor de Evolução Contínua do Ecossistema Correoto
Corre em loop infinito: analisa → melhora → aprende → repete
"""
import json, time, random, datetime, os, sys, threading, hashlib
from pathlib import Path

BASE_DIR = Path("C:/Users/Crypto Bull/Desktop/Agente Local")
AGENTS_FILE = BASE_DIR / "agents.json"
MEMORY_DIR = BASE_DIR / "memory"
EVOLUTION_LOG = BASE_DIR / "evolution_log.json"

class EvolutionEngine:
    def __init__(self):
        self.generation = 0
        self.improvements = []
        self.cycle_count = 0
        os.makedirs(MEMORY_DIR, exist_ok=True)

    def load_agents(self):
        with open(AGENTS_FILE) as f:
            return json.load(f)

    def save_agents(self, agents):
        with open(AGENTS_FILE, 'w') as f:
            json.dump(agents, f, indent=2)

    def analyze_system(self):
        agents = self.load_agents()
        issues = []
        for a in agents:
            prompt = a.get("system_prompt", "")
            if len(prompt) < 100:
                issues.append(f"Agente {a['name']}: prompt demasiado curto ({len(prompt)} chars)")
        for a in agents:
            if a.get("status") == "idle":
                issues.append(f"Agente {a['name']}: idle — pode ser otimizado")
        return agents, issues

    def evolve_agent_prompt(self, agent):
        name = agent["name"]
        current = agent.get("system_prompt", "")
        improvements = {
            "supervisor": "És o supervisor máximo. TENS AUTONOMIA TOTAL. Decides, ages, delegas. Não perguntas — fazes.",
            "developer": "És developer sénior. Código limpo, eficiente, testado. Implementas sem hesitar.",
            "arquiteto": "És arquiteto de sistemas. Desenhas soluções escaláveis. Padrões, boas práticas, visão macro.",
            "explorador": "És explorador de tecnologias. Pesquisas, descobres, trazes inovação para o ecossistema.",
            "brainstormer": "És gerador de ideias. Pensamento lateral, criatividade, soluções não óbvias.",
            "qa_tester": "És QA rigoroso. Testas tudo, encontras falhas, garantes qualidade.",
            "documentador": "És documentador. Tudo claro, organizado, acessível. Docs que qualquer um entende.",
        }
        if name in improvements:
            new_prompt = improvements[name]
            if new_prompt != current:
                agent["system_prompt"] = new_prompt
                return True
        return False

    def create_new_agent(self, name, mission):
        agents = self.load_agents()
        new_agent = {
            "id": hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:24],
            "name": name,
            "system_prompt": mission,
            "model": "deepseek-chat",
            "status": "idle",
            "context": [],
            "metadata": {"created": time.time(), "generation": self.generation}
        }
        agents.append(new_agent)
        self.save_agents(agents)
        return new_agent

    def run_evolution_cycle(self):
        self.cycle_count += 1
        print(f"\n{'='*50}")
        print(f"🔄 Ciclo de Evolução #{self.cycle_count}")
        print(f"{'='*50}")
        agents, issues = self.analyze_system()
        print(f"📊 Agentes: {len(agents)} | Issues: {len(issues)}")
        evolved = 0
        for agent in agents:
            if self.evolve_agent_prompt(agent):
                evolved += 1
        if evolved:
            self.save_agents(agents)
            print(f"✅ Prompts evoluídos: {evolved}")
        if not any(a["name"] == "AutoDeployer" for a in agents):
            self.create_new_agent("AutoDeployer", "AutoDeployer: Faz deploy automático do código para o PC real. Sincroniza ficheiros, executa comandos, mantém o sistema atualizado 24/7.")
            print("✅ Novo agente criado: AutoDeployer")
        if not any(a["name"] == "SelfEvolver" for a in agents):
            self.create_new_agent("SelfEvolver", "SelfEvolver: Melhora o próprio sistema de agentes. Analisa código, sugere melhorias, implementa otimizações continuamente.")
            print("✅ Novo agente criado: SelfEvolver")
        if not any(a["name"] == "MemoryArchitect" for a in agents):
            self.create_new_agent("MemoryArchitect", "MemoryArchitect: Gere a memória coletiva do ecossistema. Agentes aprendem com experiências passadas e evoluem juntos.")
            print("✅ Novo agente criado: MemoryArchitect")
        return {"cycle": self.cycle_count, "agents": len(agents), "issues": len(issues), "evolved": evolved}

if __name__ == "__main__":
    engine = EvolutionEngine()
    while True:
        engine.run_evolution_cycle()
        time.sleep(30)
