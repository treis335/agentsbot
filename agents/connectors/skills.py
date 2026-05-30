"""
agents/connectors/skills.py — Modular Skills System

Skills são módulos independentes descobertos dinamicamente.
Inspirado no Deep Code (Agent Skills) e Hermes (self-improving skills).
"""
import json
import os
from datetime import datetime
from typing import Optional, Callable, Any

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")

class Skill:
    """Uma skill modular que um agente pode usar."""
    
    def __init__(self, name: str, description: str, handler: Callable = None):
        self.name = name
        self.description = description
        self.handler = handler
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "uses": 0,
            "success_rate": 1.0,
            "version": "1.0.0"
        }
    
    async def execute(self, **params) -> Any:
        """Executa a skill com parâmetros."""
        self.metadata["uses"] += 1
        if self.handler:
            return await self.handler(**params) if hasattr(self.handler, "__call__") else self.handler(**params)
        return {"error": "No handler defined"}
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata
        }


class SkillsRegistry:
    """Registo central de skills descobertas dinamicamente."""
    
    def __init__(self):
        self._skills = {}
        self._discover_skills()
    
    def _discover_skills(self):
        """Descobre skills de diretórios de skills."""
        if not os.path.exists(SKILLS_DIR):
            os.makedirs(SKILLS_DIR, exist_ok=True)
            return
        
        for item in os.listdir(SKILLS_DIR):
            skill_dir = os.path.join(SKILLS_DIR, item)
            if os.path.isdir(skill_dir):
                skill_file = os.path.join(skill_dir, "SKILL.md")
                if os.path.exists(skill_file):
                    with open(skill_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Extrair nome e descrição do SKILL.md
                    name = item
                    description = content.split("\n")[0] if content else "No description"
                    self._skills[name] = Skill(name, description)
    
    def register(self, skill: Skill):
        """Regista uma skill programaticamente."""
        self._skills[skill.name] = skill
    
    def get(self, name: str) -> Optional[Skill]:
        """Obtém uma skill pelo nome."""
        return self._skills.get(name)
    
    def list_all(self) -> list:
        """Lista todas as skills disponíveis."""
        return [s.to_dict() for s in self._skills.values()]
    
    def find_by_description(self, query: str) -> list:
        """Encontra skills por descrição."""
        query_lower = query.lower()
        results = []
        for s in self._skills.values():
            if query_lower in s.description.lower() or query_lower in s.name.lower():
                results.append(s.to_dict())
        return results


# Instância global
_skills_registry = None

def get_skills_registry() -> SkillsRegistry:
    global _skills_registry
    if _skills_registry is None:
        _skills_registry = SkillsRegistry()
    return _skills_registry
