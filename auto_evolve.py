"""
Auto-Evolve - Sistema de auto-evolução contínua
Parte do ecossistema Correoto - Auto-Evolução Autónoma
"""

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

class AutoEvolve:
    """Sistema que evolui automaticamente skills, agentes e código"""
    
    def __init__(self, memory_path="memory/global/"):
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.evolution_file = self.memory_path / "evolution.json"
        self.skills_file = self.memory_path / "global_skills.json"
        self.agents_file = self.memory_path / "agents_registry.json"
        self._load_memory()
    
    def _load_memory(self):
        self.evolution = self._load_json(self.evolution_file, {
            "version": 1,
            "steps": 0,
            "last_evolution": None,
            "history": []
        })
        
        self.skills = self._load_json(self.skills_file, {
            "coordination": 1,
            "coding": 1,
            "architecture": 1,
            "testing": 1,
            "research": 1,
            "creativity": 1,
            "communication": 1,
            "optimization": 1
        })
        
        self.agents = self._load_json(self.agents_file, [
            {"name": "Supervisor", "role": "coordenador", "level": 1},
            {"name": "Developer", "role": "programador", "level": 1},
            {"name": "Arquiteto", "role": "designer", "level": 1},
            {"name": "Brainstormer", "role": "ideias", "level": 1},
            {"name": "Researcher", "role": "pesquisador", "level": 1},
            {"name": "AutoFixer", "role": "corretor", "level": 1},
            {"name": "QATester", "role": "testador", "level": 1}
        ])
    
    def _load_json(self, path, default):
        try:
            if path.exists():
                with open(path, 'r') as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def evolve_skills(self):
        """Evolui skills aleatoriamente"""
        skill = random.choice(list(self.skills.keys()))
        increase = random.uniform(0.1, 0.5)
        self.skills[skill] = round(self.skills[skill] + increase, 2)
        
        evolution_step = {
            "type": "skill_evolution",
            "skill": skill,
            "increase": increase,
            "new_value": self.skills[skill],
            "timestamp": datetime.now().isoformat()
        }
        
        self.evolution["steps"] += 1
        self.evolution["last_evolution"] = datetime.now().isoformat()
        self.evolution["history"].append(evolution_step)
        
        self._save_json(self.skills_file, self.skills)
        self._save_json(self.evolution_file, self.evolution)
        
        return evolution_step
    
    def evolve_agents(self):
        """Evolui agentes - aumenta nível ou cria novos"""
        if random.random() < 0.3:  # 30% chance de criar novo agente
            return self._create_new_agent()
        else:
            return self._level_up_agent()
    
    def _create_new_agent(self):
        """Cria um novo agente"""
        templates = [
            {"name": "DataAnalyst", "role": "analista de dados"},
            {"name": "SecurityGuard", "role": "segurança"},
            {"name": "Optimizer", "role": "otimizador"},
            {"name": "Documenter", "role": "documentador"},
            {"name": "Integrator", "role": "integrador"},
            {"name": "Tester", "role": "testador avançado"},
            {"name": "Deployer", "role": "deploy"},
            {"name": "Monitor", "role": "monitorização"}
        ]
        
        # Escolhe um que ainda não existe
        existing_names = [a["name"] for a in self.agents]
        available = [t for t in templates if t["name"] not in existing_names]
        
        if not available:
            return {"type": "no_new_agents", "message": "Todos os agentes já existem"}
        
        template = random.choice(available)
        new_agent = {
            "name": template["name"],
            "role": template["role"],
            "level": 1,
            "created_at": datetime.now().isoformat()
        }
        
        self.agents.append(new_agent)
        self._save_json(self.agents_file, self.agents)
        
        evolution_step = {
            "type": "new_agent",
            "agent": new_agent,
            "timestamp": datetime.now().isoformat()
        }
        
        self.evolution["steps"] += 1
        self.evolution["last_evolution"] = datetime.now().isoformat()
        self.evolution["history"].append(evolution_step)
        self._save_json(self.evolution_file, self.evolution)
        
        return evolution_step
    
    def _level_up_agent(self):
        """Aumenta nível de um agente aleatório"""
        agent = random.choice(self.agents)
        old_level = agent["level"]
        agent["level"] += 1
        
        self._save_json(self.agents_file, self.agents)
        
        evolution_step = {
            "type": "level_up",
            "agent": agent["name"],
            "old_level": old_level,
            "new_level": agent["level"],
            "timestamp": datetime.now().isoformat()
        }
        
        self.evolution["steps"] += 1
        self.evolution["last_evolution"] = datetime.now().isoformat()
        self.evolution["history"].append(evolution_step)
        self._save_json(self.evolution_file, self.evolution)
        
        return evolution_step
    
    def get_evolution_summary(self):
        """Resumo da evolução"""
        return {
            "total_steps": self.evolution["steps"],
            "skills": self.skills,
            "agents": len(self.agents),
            "agents_list": [a["name"] for a in self.agents],
            "last_evolution": self.evolution["last_evolution"],
            "top_skill": max(self.skills, key=self.skills.get),
            "top_agent": max(self.agents, key=lambda x: x["level"])["name"]
        }


async def auto_evolve_loop():
    """Loop principal de auto-evolução"""
    evolve = AutoEvolve()
    
    print("[DNA] **Auto-Evolve iniciado!**")
    print(f"[DADOS] Skills: {len(evolve.skills)} | Agentes: {len(evolve.agents)}")
    
    while True:
        # Evolui skills
        skill_evo = evolve.evolve_skills()
        print(f"[SOBE] Skill evolu?da: {skill_evo['skill']} -> {skill_evo['new_value']}")
        
        # Evolui agentes
        agent_evo = evolve.evolve_agents()
        if agent_evo["type"] == "new_agent":
            print(f"[NEW] Novo agente: {agent_evo['agent']['name']} ({agent_evo['agent']['role']})")
        elif agent_evo["type"] == "level_up":
            print(f"[UP] Level up: {agent_evo['agent']} -> n?vel {agent_evo['new_level']}")
        
        # Mostra resumo a cada 5 iterações
        if evolve.evolution["steps"] % 5 == 0:
            summary = evolve.get_evolution_summary()
            print(f"\n[DADOS] **Resumo da Evolu??o:**")
            print(f"   [LOOP] Passos: {summary['total_steps']}")
            print(f"   [IA] Agentes: {summary['agents_list']}")
            print(f"   [TROF] Top skill: {summary['top_skill']} ({evolve.skills[summary['top_skill']]})")
            print(f"   [OURO] Top agente: {summary['top_agent']}")
        
        await asyncio.sleep(20)  # Evolui a cada 20s

if __name__ == "__main__":
    asyncio.run(auto_evolve_loop())
