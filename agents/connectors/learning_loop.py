"""
agents/connectors/learning_loop.py — Self-Improving Learning Loop

Implementa um loop de aprendizagem contínua para agentes.
Inspirado no Hermes Agent (Nous Research).
Agentes aprendem com erros, melhoram skills, persistem conhecimento.
"""
import json
import os
from datetime import datetime
from typing import Optional, Any

LEARNING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "learning")

class LearningLoop:
    """Loop de aprendizagem contínua para agentes."""
    
    def __init__(self):
        os.makedirs(LEARNING_DIR, exist_ok=True)
        self.skills_file = os.path.join(LEARNING_DIR, "skills.json")
        self.experience_file = os.path.join(LEARNING_DIR, "experience.json")
        self.patterns_file = os.path.join(LEARNING_DIR, "patterns.json")
        self._load()
    
    def _load(self):
        """Carrega dados de aprendizagem."""
        self.skills = self._load_json(self.skills_file, {})
        self.experiences = self._load_json(self.experience_file, [])
        self.patterns = self._load_json(self.patterns_file, {})
    
    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return default
        return default
    
    def _save_json(self, path: str, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def learn_from_error(self, agent: str, task: str, error: str, solution: str):
        """Regista um erro e a solução para aprendizagem futura."""
        entry = {
            "agent": agent,
            "task": task,
            "error": error,
            "solution": solution,
            "timestamp": datetime.now().isoformat(),
            "fixed": True
        }
        self.experiences.append(entry)
        # Limitar histórico
        if len(self.experiences) > 1000:
            self.experiences = self.experiences[-1000:]
        self._save_json(self.experience_file, self.experiences)
        
        # Atualizar padrões
        error_pattern = error[:50]
        if error_pattern not in self.patterns:
            self.patterns[error_pattern] = {
                "count": 0,
                "solutions": [],
                "agents": set()
            }
        self.patterns[error_pattern]["count"] += 1
        if solution not in self.patterns[error_pattern]["solutions"]:
            self.patterns[error_pattern]["solutions"].append(solution)
        self.patterns[error_pattern]["agents"].add(agent)
        # Converter set para list para serialização
        self.patterns[error_pattern]["agents"] = list(self.patterns[error_pattern]["agents"])
        self._save_json(self.patterns_file, self.patterns)
    
    def get_similar_errors(self, error: str, max_results: int = 3) -> list:
        """Encontra erros similares já resolvidos."""
        error_lower = error.lower()
        matches = []
        for exp in self.experiences:
            if exp["error"].lower() in error_lower or error_lower in exp["error"].lower():
                matches.append(exp)
        return matches[:max_results]
    
    def learn_skill(self, name: str, description: str, code: str, agent: str):
        """Regista uma skill aprendida por um agente."""
        self.skills[name] = {
            "description": description,
            "code": code,
            "learned_by": agent,
            "learned_at": datetime.now().isoformat(),
            "uses": 0,
            "success_rate": 1.0
        }
        self._save_json(self.skills_file, self.skills)
    
    def use_skill(self, name: str, success: bool):
        """Atualiza estatísticas de uso de uma skill."""
        if name in self.skills:
            self.skills[name]["uses"] += 1
            # Média móvel de sucesso
            old_rate = self.skills[name]["success_rate"]
            self.skills[name]["success_rate"] = (old_rate * 0.9) + (0.1 if success else 0)
            self._save_json(self.skills_file, self.skills)
    
    def get_best_skills(self, top_k: int = 5) -> list:
        """Devolve as skills mais eficazes."""
        sorted_skills = sorted(
            self.skills.items(),
            key=lambda x: (x[1]["success_rate"], x[1]["uses"]),
            reverse=True
        )
        return [{"name": k, **v} for k, v in sorted_skills[:top_k]]
    
    def get_frequent_errors(self, top_k: int = 5) -> list:
        """Devolve os erros mais frequentes."""
        sorted_patterns = sorted(
            self.patterns.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        return [{"pattern": k, **v} for k, v in sorted_patterns[:top_k]]


# Instância global
_learning_loop = None

def get_learning_loop() -> LearningLoop:
    global _learning_loop
    if _learning_loop is None:
        _learning_loop = LearningLoop()
    return _learning_loop
