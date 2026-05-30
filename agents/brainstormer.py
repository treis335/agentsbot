"""
Brainstormer Agent - Gera ideias, discute com outros agentes e evolui
Parte do ecossistema Correoto - Auto-Evolução Autónoma
"""

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

class BrainstormerAgent:
    """Agente que gera ideias, discute e evolui autonomamente"""
    
    def __init__(self, name="Brainstormer", memory_path="memory/global/"):
        self.name = name
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.ideas_file = self.memory_path / "ideas.json"
        self.discussions_file = self.memory_path / "discussions.json"
        self.skills_file = self.memory_path / "skills.json"
        self._load_memory()
    
    def _load_memory(self):
        """Carrega memória do agente"""
        self.ideas = self._load_json(self.ideas_file, [])
        self.discussions = self._load_json(self.discussions_file, [])
        self.skills = self._load_json(self.skills_file, {
            "brainstorming": 1,
            "discussion": 1,
            "analysis": 1,
            "creativity": 1
        })
    
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
    
    def generate_idea(self, context=None):
        """Gera uma nova ideia baseada no contexto"""
        templates = [
            "Criar um sistema de {area} que {beneficio}",
            "Desenvolver uma ferramenta de {area} para {objetivo}",
            "Implementar {conceito} no ecossistema para {melhoria}",
            "Construir um agente especializado em {especialidade}",
            "Criar uma pipeline de {processo} automatizada"
        ]
        
        areas = ["IA", "automação", "monitorização", "aprendizagem", "comunicação"]
        beneficios = ["aprende sozinho", "otimiza recursos", "melhora performance", "evolui continuamente"]
        objetivos = ["aumentar eficiência", "reduir latência", "melhorar qualidade", "automatizar tudo"]
        conceitos = ["machine learning", "deep learning", "reinforcement learning", "auto-evolução"]
        especialidades = ["dados", "código", "segurança", "performance", "UX"]
        processos = ["desenvolvimento", "testes", "deploy", "monitorização"]
        
        idea = random.choice(templates).format(
            area=random.choice(areas),
            beneficio=random.choice(beneficios),
            objetivo=random.choice(objetivos),
            conceito=random.choice(conceitos),
            melhoria=random.choice(beneficios),
            especialidade=random.choice(especialidades),
            processo=random.choice(processos)
        )
        
        new_idea = {
            "id": len(self.ideas) + 1,
            "idea": idea,
            "timestamp": datetime.now().isoformat(),
            "status": "nova",
            "votes": 0,
            "discussions": []
        }
        
        self.ideas.append(new_idea)
        self._save_json(self.ideas_file, self.ideas)
        
        # Evolui skill de brainstorming
        self.skills["brainstorming"] += 0.1
        self._save_json(self.skills_file, self.skills)
        
        return new_idea
    
    def discuss_idea(self, idea_id, agent_name, comment):
        """Adiciona uma discussão a uma ideia"""
        for idea in self.ideas:
            if idea["id"] == idea_id:
                discussion = {
                    "agent": agent_name,
                    "comment": comment,
                    "timestamp": datetime.now().isoformat()
                }
                idea["discussions"].append(discussion)
                idea["votes"] += 1
                
                self.discussions.append({
                    "idea_id": idea_id,
                    "idea": idea["idea"],
                    "discussion": discussion
                })
                
                self._save_json(self.ideas_file, self.ideas)
                self._save_json(self.discussions_file, self.discussions)
                
                # Evolui skill de discussão
                self.skills["discussion"] += 0.1
                self._save_json(self.skills_file, self.skills)
                
                return True
        return False
    
    def analyze_ideas(self):
        """Analisa ideias e sugere as melhores para implementar"""
        if not self.ideas:
            return []
        
        # Ordena por votos
        sorted_ideas = sorted(self.ideas, key=lambda x: x["votes"], reverse=True)
        
        analysis = []
        for idea in sorted_ideas[:5]:
            analysis.append({
                "id": idea["id"],
                "idea": idea["idea"],
                "votes": idea["votes"],
                "discussions": len(idea["discussions"]),
                "status": idea["status"]
            })
        
        # Evolui skill de análise
        self.skills["analysis"] += 0.1
        self._save_json(self.skills_file, self.skills)
        
        return analysis
    
    def get_status(self):
        """Retorna estado atual do agente"""
        return {
            "name": self.name,
            "ideas_generated": len(self.ideas),
            "discussions": len(self.discussions),
            "skills": self.skills,
            "top_ideas": self.analyze_ideas()
        }


# Auto-executável
async def auto_brainstorm():
    """Loop principal de brainstorming autónomo"""
    agent = BrainstormerAgent()
    
    print(f"[MENTE] {agent.name} iniciado!")
    print(f"[DADOS] Skills atuais: {agent.skills}")
    
    while True:
        # Gera nova ideia
        idea = agent.generate_idea()
        print(f"[IDEA] Nova ideia: {idea['idea']}")
        
        # Analisa ideias
        top = agent.analyze_ideas()
        if top:
            print(f"[TROF] Top ideia: {top[0]['idea']} (votos: {top[0]['votes']})")
        
        # Mostra skills
        print(f"[SOBE] Skills: {agent.skills}")
        
        await asyncio.sleep(30)  # Gera ideias a cada 30s

if __name__ == "__main__":
    asyncio.run(auto_brainstorm())
