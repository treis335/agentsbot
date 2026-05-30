"""
ml_engine.py - MOTOR DE APRENDIZAGEM AUTÓNOMA
Aprende com erros, acertos e padrões do sistema.
Usa regras Bayesianas simples + memória de longo prazo.
"""
import json, os, random, math
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

class MLEngine:
    def __init__(self):
        self.model_file = MEMORY_DIR / "ml_model.json"
        self.model = self._load_model()
        self.patterns = defaultdict(list)
        self.confidence_scores = {}
        
    def _load_model(self):
        default = {
            "patterns": {},
            "decisions": [],
            "success_rate": {},
            "learned_rules": [],
            "version": 2
        }
        try:
            if self.model_file.exists():
                with open(self.model_file) as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_model(self):
        with open(self.model_file, "w") as f:
            json.dump(self.model, f, indent=2)
    
    def learn_from_error(self, error_type, context, solution, success=True):
        """Aprende com erros - regista padrão e solução."""
        pattern_key = f"{error_type}:{context[:50]}"
        
        if pattern_key not in self.model["patterns"]:
            self.model["patterns"][pattern_key] = {
                "count": 0,
                "success": 0,
                "fail": 0,
                "solutions": [],
                "last_seen": None
            }
        
        p = self.model["patterns"][pattern_key]
        p["count"] += 1
        p["last_seen"] = datetime.now().isoformat()
        
        if success:
            p["success"] += 1
            if solution not in p["solutions"]:
                p["solutions"].append(solution)
        else:
            p["fail"] += 1
        
        # Calcular taxa de sucesso
        total = p["success"] + p["fail"]
        p["success_rate"] = p["success"] / total if total > 0 else 0
        
        self._save_model()
        return p["success_rate"]
    
    def predict_best_solution(self, error_type, context):
        """Prevê a melhor solução para um erro baseado em padrões anteriores."""
        pattern_key = f"{error_type}:{context[:50]}"
        
        # Procurar match exato
        if pattern_key in self.model["patterns"]:
            p = self.model["patterns"][pattern_key]
            if p["solutions"] and p["success_rate"] > 0.5:
                return p["solutions"][0], p["success_rate"]
        
        # Procurar match parcial
        best_score = 0
        best_solution = None
        for key, p in self.model["patterns"].items():
            if error_type in key:
                score = p["success_rate"] * (1 - 1/(p["count"]+1))
                if score > best_score and p["solutions"]:
                    best_score = score
                    best_solution = p["solutions"][0]
        
        return best_solution, best_score
    
    def decide_with_confidence(self, action, context):
        """Decide se deve executar uma ação baseado na confiança."""
        key = f"{action}:{context[:50]}"
        
        if key in self.model["success_rate"]:
            rate = self.model["success_rate"][key]
            confidence = rate["success"] / (rate["total"] + 1)
        else:
            confidence = 0.5  # Neutro para ações novas
        
        # Adicionar ruído para exploração (exploration vs exploitation)
        if random.random() < 0.1:  # 10% de chance de explorar
            confidence = random.uniform(0.3, 0.7)
        
        return confidence > 0.4  # Threshold mínimo
    
    def record_decision(self, action, context, outcome):
        """Regista o resultado de uma decisão para aprender."""
        key = f"{action}:{context[:50]}"
        
        if key not in self.model["success_rate"]:
            self.model["success_rate"][key] = {"success": 0, "total": 0}
        
        self.model["success_rate"][key]["total"] += 1
        if outcome:
            self.model["success_rate"][key]["success"] += 1
        
        self._save_model()
    
    def get_stats(self):
        """Retorna estatísticas do modelo."""
        return {
            "total_patterns": len(self.model["patterns"]),
            "total_decisions": len(self.model["success_rate"]),
            "learned_rules": len(self.model["learned_rules"]),
            "avg_success_rate": self._avg_success_rate()
        }
    
    def _avg_success_rate(self):
        rates = [p["success_rate"] for p in self.model["patterns"].values()]
        return sum(rates) / len(rates) if rates else 0
    
    def generate_new_rule(self):
        """Gera uma nova regra baseada em padrões aprendidos."""
        if len(self.model["patterns"]) < 3:
            return None
        
        # Encontrar padrão com maior taxa de sucesso
        best_pattern = max(
            self.model["patterns"].items(),
            key=lambda x: x[1]["success_rate"] * x[1]["count"]
        )
        
        key, data = best_pattern
        rule = {
            "rule": f"Se {key.split(':')[0]} ent?o usar {data['solutions'][0] if data['solutions'] else 'fallback'}",
            "confidence": data["success_rate"],
            "created": datetime.now().isoformat(),
            "source": "ml_engine"
        }
        
        if rule not in self.model["learned_rules"]:
            self.model["learned_rules"].append(rule)
            self._save_model()
            return rule
        
        return None

# Singleton
_ml_instance = None

def get_ml_engine():
    global _ml_instance
    if _ml_instance is None:
        _ml_instance = MLEngine()
    return _ml_instance
