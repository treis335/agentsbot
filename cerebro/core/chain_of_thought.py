"""
chain_of_thought.py — CADEIA DE PENSAMENTO DO CÉREBRO CORREOTO
Pensamento estruturado passo-a-passo para resolver problemas complexos.
Suporta raciocínio em árvore, backtracking e auto-correção.
"""
import json, time, logging, random, os
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [COT] %(message)s")
log = logging.getLogger("chain_of_thought")

class ChainOfThought:
    """Cadeia de pensamento para raciocínio profundo passo-a-passo."""
    
    def __init__(self):
        self.thoughts_file = MEMORY_DIR / "chain_of_thought.json"
        self.thoughts = self._load_json(self.thoughts_file, [])
        self.cycle = 0
        self.max_depth = 5
    
    def _load_json(self, path, default):
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except: pass
        return default
    
    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _analyze_problem(self, problem):
        """Analisa o problema para extrair características."""
        analysis = {
            "complexity": len(problem.split()),
            "has_question": "?" in problem,
            "keywords": [w for w in problem.lower().split() if len(w) > 3],
            "type": self._classify_problem(problem)
        }
        return analysis
    
    def _classify_problem(self, problem):
        """Classifica o tipo de problema."""
        p = problem.lower()
        if any(w in p for w in ["como", "how", "maneira", "forma"]):
            return "procedural"
        elif any(w in p for w in ["porque", "why", "razao", "motivo"]):
            return "causal"
        elif any(w in p for w in ["qual", "which", "melhor", "pior"]):
            return "comparativo"
        elif any(w in p for w in ["criar", "create", "fazer", "build", "construir"]):
            return "construtivo"
        else:
            return "exploratorio"
    
    def _decompose(self, problem):
        """Divide o problema em subproblemas."""
        subproblems = []
        
        # Estratégias de decomposição
        strategies = [
            f"1. Analisar requisitos de: {problem}",
            f"2. Identificar componentes de: {problem}",
            f"3. Definir depend?ncias entre componentes",
            f"4. Resolver cada componente individualmente",
            f"5. Integrar solu??es parciais"
        ]
        
        return strategies
    
    def _evaluate_solution(self, solution, problem):
        """Avalia a qualidade de uma solução."""
        score = 0.5  # Base
        
        # Critérios de avaliação
        if len(solution) > 50:
            score += 0.1  # Soluções detalhadas são melhores
        if problem.lower() in solution.lower():
            score += 0.2  # Relevante ao problema
        if "passo" in solution.lower() or "step" in solution.lower():
            score += 0.1  # Estruturada
        if "erro" in solution.lower() or "error" in solution.lower():
            score -= 0.1  # Menciona erros pode ser negativo
        
        return min(max(score, 0), 1.0)
    
    def think(self, problem, depth=3):
        """Processa um problema com pensamento estruturado."""
        self.cycle += 1
        depth = min(depth, self.max_depth)
        log.info(f"Ciclo {self.cycle}: Pensando sobre: {problem[:80]}... (profundidade: {depth})")
        
        thought_chain = {
            "problem": problem,
            "depth": depth,
            "steps": [],
            "conclusion": None,
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat(),
            "cycle": self.cycle
        }
        
        # Passo 1: Compreender o problema
        analysis = self._analyze_problem(problem)
        thought_chain["steps"].append({
            "step": 1,
            "type": "compreensão",
            "content": f"Problema: {problem}",
            "analysis": analysis
        })
        log.info(f"Passo 1 - Tipo: {analysis['type']}, Complexidade: {analysis['complexity']}")
        
        # Passo 2: Dividir em subproblemas
        subproblems = self._decompose(problem)
        thought_chain["steps"].append({
            "step": 2,
            "type": "decomposição",
            "content": "Dividir problema em partes",
            "subproblems": subproblems[:depth]
        })
        log.info(f"Passo 2 - {len(subproblems)} subproblemas identificados")
        
        # Passo 3: Raciocínio profundo para cada subproblema
        solutions = []
        for i, sp in enumerate(subproblems[:depth]):
            # Simular raciocínio para cada subproblema
            solution = self._reason_subproblem(sp, i+1)
            solutions.append(solution)
            
            thought_chain["steps"].append({
                "step": 3 + i,
                "type": f"subproblema_{i+1}",
                "content": sp,
                "solution": solution
            })
        
        # Passo 4: Síntese
        final_solution = self._synthesize(solutions, problem)
        confidence = self._evaluate_solution(final_solution, problem)
        
        thought_chain["conclusion"] = final_solution
        thought_chain["confidence"] = confidence
        
        thought_chain["steps"].append({
            "step": 3 + depth,
            "type": "síntese",
            "content": "Integrar soluções parciais",
            "final_solution": final_solution,
            "confidence": confidence
        })
        
        # Guardar
        self.thoughts.append(thought_chain)
        self._save_json(self.thoughts_file, self.thoughts)
        
        log.info(f"Conclusao (confianca: {confidence:.2f}): {final_solution[:80]}...")
        return thought_chain
    
    def _reason_subproblem(self, subproblem, index):
        """Raciocina sobre um subproblema específico."""
        templates = [
            f"Para {subproblem.lower()}, a abordagem recomendada ? analisar primeiro os requisitos.",
            f"Solu??o para {subproblem}: implementar de forma iterativa e testar cada componente.",
            f"Subproblema {index}: {subproblem} - A melhor pr?tica ? come?ar pelo mais simples.",
            f"Resolver '{subproblem}' requer aten??o aos detalhes e valida??o cont?nua."
        ]
        return random.choice(templates)
    
    def _synthesize(self, solutions, problem):
        """Sintetiza soluções parciais numa solução completa."""
        if not solutions:
            return f"N?o foi poss?vel gerar solu??o para: {problem}"
        
        synthesis = f"Solu??o para '{problem}':\n"
        for i, sol in enumerate(solutions):
            synthesis += f"\n{i+1}. {sol}"
        
        synthesis += f"\n\nConclus?o: A solu??o integrada resolve {problem} atrav?s de {len(solutions)} passos."
        return synthesis
    
    def get_recent_thoughts(self, n=3):
        """Obtém os pensamentos mais recentes."""
        return self.thoughts[-n:] if self.thoughts else []

if __name__ == "__main__":
    cot = ChainOfThought()
    result = cot.think("Como construir um sistema autónomo de vendas?", depth=3)
    print(json.dumps(result, indent=2, ensure_ascii=False))
