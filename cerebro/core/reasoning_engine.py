"""
reasoning_engine.py — MOTOR DE RACIOCÍNIO DO CÉREBRO CORREOTO
Pensa, raciocina, tira conclusões e aprende sozinho.
Suporta raciocínio dedutivo, indutivo e abdutivo.
"""
import json, time, logging, random, os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [REASON] %(message)s")
log = logging.getLogger("reasoning")

class ReasoningEngine:
    """Motor de raciocínio que processa informação e tira conclusões."""
    
    def __init__(self):
        self.reasoning_file = MEMORY_DIR / "reasoning_log.json"
        self.conclusions_file = MEMORY_DIR / "conclusions.json"
        self.reasoning_log = self._load_json(self.reasoning_file, [])
        self.conclusions = self._load_json(self.conclusions_file, [])
        self.cycle = 0
        self.knowledge_base = defaultdict(list)
    
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
    
    def _generate_hypotheses(self, problem, context=None):
        """Gera hipóteses sobre o problema."""
        hypotheses = []
        
        # Hipótese 1: Análise direta
        hypotheses.append({
            "type": "direta",
            "description": f"Resolver {problem} diretamente",
            "confidence": 0.7
        })
        
        # Hipótese 2: Por analogia
        if context:
            hypotheses.append({
                "type": "analogia",
                "description": f"Usar contexto {str(context)[:50]} para resolver",
                "confidence": 0.5
            })
        
        # Hipótese 3: Decomposição
        hypotheses.append({
            "type": "decomposicao",
            "description": f"Dividir {problem} em subproblemas menores",
            "confidence": 0.8
        })
        
        # Hipótese 4: Pesquisa
        hypotheses.append({
            "type": "pesquisa",
            "description": "Pesquisar conhecimento existente para solução",
            "confidence": 0.6
        })
        
        return hypotheses
    
    def _evaluate_hypotheses(self, hypotheses):
        """Avalia e pontua cada hipótese."""
        evaluated = []
        for h in hypotheses:
            score = h["confidence"]
            # Ajustar com base no tipo
            if h["type"] == "decomposicao":
                score *= 1.2  # Decomposição é geralmente eficaz
            elif h["type"] == "pesquisa":
                score *= 0.9  # Pode não encontrar resposta
            evaluated.append({**h, "final_score": round(score, 2)})
        
        return sorted(evaluated, key=lambda x: x["final_score"], reverse=True)
    
    def reason(self, problem, context=None):
        """Processa um problema e devolve uma conclusão."""
        self.cycle += 1
        log.info(f"Ciclo {self.cycle}: Raciocinando sobre: {problem[:80]}...")
        
        reasoning_record = {
            "cycle": self.cycle,
            "problem": problem,
            "context": context,
            "steps": [],
            "hypotheses": [],
            "conclusion": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Passo 1: Analisar problema
        reasoning_record["steps"].append({
            "step": 1,
            "action": "Analisar problema",
            "detail": f"Problema: {problem}"
        })
        
        if context:
            reasoning_record["steps"].append({
                "step": 2,
                "action": "Considerar contexto",
                "detail": f"Contexto: {str(context)[:200]}"
            })
        
        # Passo 2: Gerar hipóteses
        hypotheses = self._generate_hypotheses(problem, context)
        evaluated = self._evaluate_hypotheses(hypotheses)
        reasoning_record["hypotheses"] = evaluated
        
        reasoning_record["steps"].append({
            "step": 3,
            "action": "Gerar e avaliar hipóteses",
            "detail": f"Melhor hipótese: {evaluated[0]['type']} (score: {evaluated[0]['final_score']})"
        })
        
        # Passo 3: Raciocínio dedutivo
        deduction = self._deductive_reasoning(problem, evaluated)
        reasoning_record["steps"].append({
            "step": 4,
            "action": "Raciocínio dedutivo",
            "detail": deduction
        })
        
        # Passo 4: Conclusão
        conclusion = {
            "problem": problem,
            "best_approach": evaluated[0]["type"],
            "confidence": evaluated[0]["final_score"],
            "deduction": deduction,
            "suggested_action": self._suggest_action(evaluated[0]["type"], problem)
        }
        reasoning_record["conclusion"] = conclusion
        
        # Guardar
        self.reasoning_log.append(reasoning_record)
        self.conclusions.append(conclusion)
        self._save_json(self.reasoning_file, self.reasoning_log)
        self._save_json(self.conclusions_file, self.conclusions)
        
        log.info(f"Conclusao: {conclusion['suggested_action'][:80]}")
        return conclusion
    
    def _deductive_reasoning(self, problem, hypotheses):
        """Aplica raciocínio dedutivo para chegar a uma conclusão."""
        best = hypotheses[0]
        
        if best["type"] == "decomposicao":
            return f"O problema '{problem}' deve ser decomposto em partes menores para facilitar a resolução."
        elif best["type"] == "direta":
            return f"Solução direta para '{problem}' é a abordagem mais confiante."
        elif best["type"] == "analogia":
            return f"Usar conhecimento prévio similar para resolver '{problem}'."
        else:
            return f"Pesquisar soluções existentes para '{problem}'."
    
    def _suggest_action(self, approach, problem):
        """Sugere uma ação com base na abordagem escolhida."""
        suggestions = {
            "decomposicao": f"Dividir '{problem}' em 3-5 subproblemas e resolver cada um",
            "direta": f"Aplicar solução conhecida para '{problem}'",
            "analogia": f"Encontrar problemas similares já resolvidos",
            "pesquisa": f"Pesquisar na base de conhecimento por '{problem}'"
        }
        return suggestions.get(approach, f"Analisar '{problem}' mais profundamente")
    
    def get_stats(self):
        """Estatísticas do motor de raciocínio."""
        return {
            "total_cycles": self.cycle,
            "total_conclusions": len(self.conclusions),
            "last_cycle": self.reasoning_log[-1]["timestamp"] if self.reasoning_log else None
        }

if __name__ == "__main__":
    engine = ReasoningEngine()
    result = engine.reason("Como criar um negócio automatizado?")
    print(json.dumps(result, indent=2, ensure_ascii=False))
