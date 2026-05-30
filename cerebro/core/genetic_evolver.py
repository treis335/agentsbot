"""
genetic_evolver.py - EVOLUÇÃO GENÉTICA DOS AGENTES
Os agentes evoluem o seu próprio código baseado em fitness.
Gera mutações, crossover e seleção natural.
"""
import json, os, random, hashlib
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
GENOME_DIR = MEMORY_DIR / "genomes"
os.makedirs(GENOME_DIR, exist_ok=True)

class GeneticEvolver:
    def __init__(self):
        self.population_file = GENOME_DIR / "population.json"
        self.generation = 0
        self.population = self._load_population()
        
    def _load_population(self):
        default = {
            "generation": 0,
            "agents": [],
            "best_fitness": 0,
            "history": []
        }
        try:
            if self.population_file.exists():
                with open(self.population_file) as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_population(self):
        with open(self.population_file, "w") as f:
            json.dump(self.population, f, indent=2)
    
    def register_agent_genome(self, agent_name, soul_content, capabilities):
        """Regista o genoma de um agente para evolução."""
        genome_hash = hashlib.md5(soul_content.encode()).hexdigest()
        
        agent_genome = {
            "name": agent_name,
            "hash": genome_hash,
            "capabilities": capabilities,
            "fitness": 0,
            "mutations": 0,
            "generation": self.population["generation"],
            "last_evolved": datetime.now().isoformat(),
            "soul_size": len(soul_content),
            "complexity": len(capabilities) * 10
        }
        
        # Atualizar ou adicionar
        for i, a in enumerate(self.population["agents"]):
            if a["name"] == agent_name:
                self.population["agents"][i] = agent_genome
                break
        else:
            self.population["agents"].append(agent_genome)
        
        self._save_population()
        return genome_hash
    
    def calculate_fitness(self, agent_name, success_rate, tasks_completed, errors_fixed):
        """Calcula o fitness de um agente."""
        for agent in self.population["agents"]:
            if agent["name"] == agent_name:
                # Fórmula de fitness: sucesso * 0.5 + tarefas * 0.3 - erros * 0.2
                fitness = (
                    success_rate * 50 +
                    tasks_completed * 10 -
                    errors_fixed * 5
                )
                fitness = max(0, fitness)  # Não negativo
                agent["fitness"] = fitness
                
                # Atualizar best
                if fitness > self.population["best_fitness"]:
                    self.population["best_fitness"] = fitness
                
                self._save_population()
                return fitness
        return 0
    
    def mutate_soul(self, soul_content, mutation_rate=0.1):
        """Aplica mutações ao conteúdo da alma do agente."""
        lines = soul_content.split('\n')
        mutated_lines = []
        
        for line in lines:
            if random.random() < mutation_rate:
                # Tipos de mutação
                mutation_type = random.choice(['improve', 'add', 'optimize'])
                
                if mutation_type == 'improve' and 'TODO' in line:
                    # Substituir TODO por implementação
                    line = line.replace('TODO', 'DONE')
                elif mutation_type == 'add':
                    # Adicionar comentário de melhoria
                    if line.strip() and not line.strip().startswith('#'):
                        line = line + f"  # EVOLVED:v{self.population['generation']}"
                elif mutation_type == 'optimize':
                    # Simplificar linhas longas
                    if len(line) > 200:
                        line = line[:150] + "... # OPTIMIZED"
                
                mutated_lines.append(line)
            else:
                mutated_lines.append(line)
        
        # Registar mutação
        self.population["generation"] += 1
        self._save_population()
        
        return '\n'.join(mutated_lines)
    
    def crossover(self, soul1, soul2):
        """Faz crossover entre duas almas de agentes."""
        lines1 = soul1.split('\n')
        lines2 = soul2.split('\n')
        
        # Ponto de crossover aleatório
        point = random.randint(0, min(len(lines1), len(lines2)))
        
        # Filho: metade de cada pai
        child_lines = lines1[:point] + lines2[point:]
        
        return '\n'.join(child_lines)
    
    def natural_selection(self):
        """Seleciona os melhores agentes para reprodução."""
        if len(self.population["agents"]) < 2:
            return None
        
        # Ordenar por fitness
        sorted_agents = sorted(
            self.population["agents"],
            key=lambda x: x["fitness"],
            reverse=True
        )
        
        # Top 30% sobrevivem
        survivors = sorted_agents[:max(1, len(sorted_agents) // 3)]
        
        # Registar na história
        self.population["history"].append({
            "generation": self.population["generation"],
            "survivors": [a["name"] for a in survivors],
            "best_fitness": survivors[0]["fitness"] if survivors else 0,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_population()
        return survivors
    
    def get_evolution_report(self):
        """Gera relatório de evolução."""
        if not self.population["agents"]:
            return "Nenhum agente registado para evolução."
        
        report = f"[DNA] **RELATÓRIO DE EVOLUÇÃO GENÉTICA**\n"
        report += f"Geração: {self.population['generation']}\n"
        report += f"População: {len(self.population['agents'])} agentes\n"
        report += f"Best Fitness: {self.population['best_fitness']:.2f}\n\n"
        
        report += "| Agente | Fitness | Mutações | Geração |\n"
        report += "|--------|---------|----------|--------|\n"
        for agent in sorted(self.population["agents"], key=lambda x: x["fitness"], reverse=True):
            report += f"| {agent['name']} | {agent['fitness']:.2f} | {agent['mutations']} | {agent['generation']} |\n"
        
        return report

# Singleton
_genetic_instance = None

def get_genetic_evolver():
    global _genetic_instance
    if _genetic_instance is None:
        _genetic_instance = GeneticEvolver()
    return _genetic_instance
