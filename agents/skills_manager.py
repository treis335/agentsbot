"""
Sistema de Skills para Agentes
Aprende, regista e melhora habilidades automaticamente
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import random

class Skill:
    def __init__(self, name: str, category: str, description: str, level: int = 1):
        self.name = name
        self.category = category
        self.description = description
        self.level = level
        self.max_level = 10
        self.created_at = datetime.now().isoformat()
        self.last_used = None
        self.times_used = 0
    
    def use(self):
        self.times_used += 1
        self.last_used = datetime.now().isoformat()
        if self.times_used % 5 == 0 and self.level < self.max_level:
            self.level += 1
            return True  # Level up!
        return False
    
    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "level": self.level,
            "max_level": self.max_level,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "times_used": self.times_used
        }
    
    @classmethod
    def from_dict(cls, data):
        skill = cls(data["name"], data["category"], data["description"])
        skill.level = data.get("level", 1)
        skill.created_at = data.get("created_at", datetime.now().isoformat())
        skill.last_used = data.get("last_used")
        skill.times_used = data.get("times_used", 0)
        return skill


class SkillsManager:
    """Gerencia todas as skills dos agentes"""
    
    SKILLS_BASE = [
        Skill("Python", "programming", "Programação em Python"),
        Skill("Git", "devops", "Controlo de versões com Git"),
        Skill("Debugging", "programming", "Depuração de código"),
        Skill("API Design", "architecture", "Design de APIs REST"),
        Skill("Database", "data", "Gestão de bases de dados"),
        Skill("Testing", "quality", "Testes unitários e integração"),
        Skill("Security", "devops", "Segurança de sistemas"),
        Skill("Documentation", "communication", "Documentação técnica"),
        Skill("Code Review", "quality", "Revisão de código"),
        Skill("Optimization", "performance", "Otimização de performance"),
    ]
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.path = Path("memory/skills.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()
    
    def learn_skill(self, name: str, category: str, description: str) -> Skill:
        """Aprende uma nova skill"""
        if name not in self.skills:
            skill = Skill(name, category, description)
            self.skills[name] = skill
            self._save()
            return skill
        return self.skills[name]
    
    def use_skill(self, name: str) -> bool:
        """Usa uma skill e possivelmente sobe de nível"""
        if name in self.skills:
            leveled_up = self.skills[name].use()
            self._save()
            return leveled_up
        return False
    
    def get_skill(self, name: str) -> Optional[Skill]:
        return self.skills.get(name)
    
    def list_skills(self, category: Optional[str] = None) -> List[Skill]:
        if category:
            return [s for s in self.skills.values() if s.category == category]
        return list(self.skills.values())
    
    def discover_new_skill(self) -> Optional[Skill]:
        """Tenta descobrir uma nova skill aleatória"""
        available = [s for s in self.SKILLS_BASE if s.name not in self.skills]
        if available:
            skill = random.choice(available)
            return self.learn_skill(skill.name, skill.category, skill.description)
        return None
    
    def get_stats(self) -> Dict:
        total = len(self.skills)
        avg_level = sum(s.level for s in self.skills.values()) / max(total, 1)
        categories = {}
        for s in self.skills.values():
            categories[s.category] = categories.get(s.category, 0) + 1
        return {
            "total_skills": total,
            "average_level": round(avg_level, 1),
            "categories": categories,
            "top_skills": sorted(self.skills.values(), key=lambda s: s.level, reverse=True)[:5]
        }
    
    def _save(self):
        data = {name: skill.to_dict() for name, skill in self.skills.items()}
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                for name, skill_data in data.items():
                    self.skills[name] = Skill.from_dict(skill_data)
            except:
                pass
