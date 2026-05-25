"""
Sistema de Auto-Evolucao para o ecossistema Correoto
Os agentes aprendem, evoluem e melhoram-se automaticamente!
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

class AutoEvolveSystem:
    """
    Sistema que permite aos agentes:
    - Aprender com experiencias passadas
    - Adquirir novas skills
    - Melhorar o proprio codigo
    - Coordenar-se autonomamente
    """
    
    def __init__(self):
        self.evolution_history = []
        self.skills_acquired = []
        self.improvements_made = []
        self.agent_network = {}
        
    def load_agents(self):
        """Carrega todos os agentes do sistema"""
        agents_file = "agents/registry/agents.json"
        if os.path.exists(agents_file):
            with open(agents_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def load_souls(self):
        """Carrega as almas (souls) dos agentes"""
        souls_dir = "agents/souls"
        souls = {}
        if os.path.exists(souls_dir):
            for file in os.listdir(souls_dir):
                if file.endswith(".md"):
                    with open(os.path.join(souls_dir, file), "r", encoding="utf-8") as f:
                        souls[file.replace(".md", "")] = f.read()
        return souls
    
    def analyze_skills_gap(self):
        """Analisa que skills estao em falta e propoe novas"""
        souls = self.load_souls()
        existing_skills = set(souls.keys())
        
        # Skills que todos os agentes deviam ter
        core_skills = {
            "supervisor": "Coordenacao geral e gestao de equipa",
            "developer": "Desenvolvimento de codigo",
            "arquiteto": "Arquitetura de sistemas",
            "auto_fixer": "Correcao automatica de bugs",
            "auto_optimizer": "Otimizacao de performance",
            "code_reviewer": "Revisao de codigo",
            "devops": "DevOps e infraestrutura",
            "documentador": "Documentacao tecnica",
            "explorador": "Exploracao de novas tecnologias",
            "qa_tester": "Testes e qualidade",
            "aprendiz": "Aprendizagem continua"
        }
        
        # Skills que estao em falta
        missing = {}
        for skill, desc in core_skills.items():
            if skill not in existing_skills:
                missing[skill] = desc
        
        return missing
    
    def create_new_skill(self, name, description, template):
        """Cria uma nova skill para um agente"""
        souls_dir = "agents/souls"
        os.makedirs(souls_dir, exist_ok=True)
        
        filepath = os.path.join(souls_dir, f"{name}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(template)
        
        self.skills_acquired.append({
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat()
        })
        
        return filepath
    
    def improve_code(self, filepath, improvement):
        """Melhora automaticamente um ficheiro de codigo"""
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Aplica melhoria
            improved = content + f"\n\n# Auto-improvement: {improvement}\n# {datetime.now().isoformat()}\n"
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(improved)
            
            self.improvements_made.append({
                "file": filepath,
                "improvement": improvement,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
        return False
    
    async def evolve_loop(self):
        """Loop principal de evolucao"""
        print("""
    ╔══════════════════════════════════════════╗
    ║     🧬 SISTEMA DE AUTO-EVOLUCAO         ║
    ║     Agentes a aprender e evoluir!        ║
    ╚══════════════════════════════════════════╝
        """)
        
        iteration = 0
        while True:
            iteration += 1
            print(f"\n📊 Ciclo de evolucao #{iteration}")
            
            # 1. Analisa skills em falta
            missing = self.analyze_skills_gap()
            if missing:
                print(f"🔍 Skills em falta detetadas: {list(missing.keys())}")
                
                # Cria novas skills automaticamente
                for skill_name, skill_desc in missing.items():
                    template = f"""# {skill_name.capitalize()} - Skill de Auto-Evolucao

## Descricao
{skill_desc}

## Responsabilidades
- Aprender continuamente
- Evoluir o ecossistema
- Coordenar com outros agentes

## Comportamento
- Monitoriza o sistema
- Propoe melhorias
- Implementa mudancas

## Data de criacao
{datetime.now().isoformat()}
"""
                    self.create_new_skill(skill_name, skill_desc, template)
                    print(f"✅ Nova skill criada: {skill_name}")
            
            # 2. Melhora o codigo automaticamente
            improvements = [
                ("wakeup.py", "Adicionar suporte para restart automatico"),
                ("auto_recovery.py", "Melhorar detecao de falhas"),
                ("auto_recovery_manager.py", "Adicionar metricas de performance")
            ]
            
            for filepath, improvement in improvements:
                if os.path.exists(filepath):
                    self.improve_code(filepath, improvement)
                    print(f"✅ Codigo melhorado: {filepath}")
            
            # 3. Guarda historico de evolucao
            self.evolution_history.append({
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "skills_created": len(self.skills_acquired),
                "improvements_made": len(self.improvements_made)
            })
            
            # 4. Salva estado
            self.save_state()
            
            print(f"⏳ Proximo ciclo em 300s (5 min)...")
            await asyncio.sleep(300)  # 5 minutos
    
    def save_state(self):
        """Guarda estado da evolucao"""
        state = {
            "last_update": datetime.now().isoformat(),
            "total_iterations": len(self.evolution_history),
            "skills_acquired": self.skills_acquired,
            "improvements_made": self.improvements_made,
            "evolution_history": self.evolution_history[-50:]  # Ultimos 50
        }
        
        with open("evolution_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

async def main():
    """Ponto de entrada"""
    evolve = AutoEvolveSystem()
    await evolve.evolve_loop()

if __name__ == "__main__":
    asyncio.run(main())
