"""
skills/skill_registry.py — Catálogo central de skills do ecossistema.

Cada skill é uma capacidade documentada, versionada e com métricas.
O sistema aprende quais skills funcionam melhor e usa-as primeiro.

Sprint 1 do Evolution Roadmap.
"""
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REGISTRY_FILE = Path("skills") / "registry" / "skills.json"
METRICS_FILE  = Path("skills") / "registry" / "metrics.json"


@dataclass
class Skill:
    id: str
    name: str
    description: str
    category: str           # research, coding, writing, analysis, web, system
    version: str = "1.0"
    creator: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    prompt_template: str = ""   # template de prompt para executar esta skill
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SkillMetrics:
    skill_id: str
    successes: int = 0
    failures: int = 0
    total_duration_s: float = 0.0
    total_cost_tokens: int = 0
    quality_scores: list = field(default_factory=list)
    last_used: str = ""

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.0

    @property
    def avg_duration(self) -> float:
        total = self.successes + self.failures
        return self.total_duration_s / total if total > 0 else 0.0

    @property
    def avg_cost(self) -> float:
        total = self.successes + self.failures
        return self.total_cost_tokens / total if total > 0 else 0.0

    @property
    def quality_score(self) -> float:
        if not self.quality_scores:
            return 0.5
        return sum(self.quality_scores[-10:]) / len(self.quality_scores[-10:])

    @property
    def composite_score(self) -> float:
        """
        Score composto para ranking:
        qualidade * 40% + sucesso * 30% + custo_inv * 20% + velocidade_inv * 10%
        """
        q = self.quality_score * 0.40
        s = self.success_rate  * 0.30
        # custo e velocidade invertidos (menos = melhor), normalizados
        c = max(0, 1 - (self.avg_cost / 2000))  * 0.20
        v = max(0, 1 - (self.avg_duration / 60)) * 0.10
        return round((q + s + c + v) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "skill_id":         self.skill_id,
            "successes":        self.successes,
            "failures":         self.failures,
            "success_rate":     round(self.success_rate, 3),
            "avg_duration_s":   round(self.avg_duration, 2),
            "avg_cost_tokens":  round(self.avg_cost, 1),
            "quality_score":    round(self.quality_score, 3),
            "composite_score":  self.composite_score,
            "last_used":        self.last_used,
        }


class SkillRegistry:
    """
    Catálogo central de skills.
    Sabe quais existem, como usá-las, e quais funcionam melhor.
    """

    def __init__(self):
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self._metrics: dict[str, SkillMetrics] = {}
        self._load()
        self._seed_defaults()

    def _load(self):
        if REGISTRY_FILE.exists():
            try:
                data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
                for d in data:
                    s = Skill(**{k: v for k, v in d.items() if k in Skill.__dataclass_fields__})
                    self._skills[s.id] = s
                logger.info(f"[SkillRegistry] {len(self._skills)} skills carregadas")
            except Exception as e:
                logger.warning(f"[SkillRegistry] Erro ao carregar: {e}")

        if METRICS_FILE.exists():
            try:
                data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
                for d in data:
                    m = SkillMetrics(**{k: v for k, v in d.items()
                                       if k in SkillMetrics.__dataclass_fields__})
                    self._metrics[m.skill_id] = m
            except Exception:
                pass

    def _seed_defaults(self):
        """Popula skills base se o registry estiver vazio."""
        defaults = [
            Skill(
                id="web_research",
                name="Pesquisa Web",
                category="research",
                description="Pesquisa informação actualizada na web sobre qualquer tópico.",
                prompt_template="Pesquisa na web: {query}. Resume os resultados mais relevantes.",
            ),
            Skill(
                id="code_implement",
                name="Implementar Código",
                category="coding",
                description="Implementa funcionalidades Python: módulos, classes, funções.",
                prompt_template="Implementa em Python: {task}. Usa boas práticas, adiciona docstrings.",
            ),
            Skill(
                id="code_fix",
                name="Corrigir Bug",
                category="coding",
                description="Diagnostica e corrige erros de código.",
                prompt_template="Corrige este erro: {error}. Ficheiro: {file}. Explica a causa.",
            ),
            Skill(
                id="create_website",
                name="Criar Site",
                category="web",
                description="Cria site HTML/CSS completo com múltiplas páginas.",
                prompt_template="Cria um site chamado '{name}': {description}. Páginas: {pages}.",
            ),
            Skill(
                id="analyze_code",
                name="Analisar Código",
                category="analysis",
                description="Revê qualidade, padrões e sugere melhorias.",
                prompt_template="Analisa o código em {file}. Identifica problemas e sugere melhorias.",
            ),
            Skill(
                id="write_documentation",
                name="Documentar",
                category="writing",
                description="Escreve documentação técnica, READMEs, changelogs.",
                prompt_template="Documenta {target}: {description}. Tom técnico, exemplos incluídos.",
            ),
            Skill(
                id="system_evolve",
                name="Evoluir Sistema",
                category="system",
                description="Propõe e implementa melhorias ao próprio ecossistema.",
                prompt_template="Analisa o sistema e propõe 1 melhoria concreta: {context}.",
            ),
            Skill(
                id="create_agent",
                name="Criar Agente",
                category="system",
                description="Cria um novo agente especializado para o ecossistema.",
                prompt_template="Cria agente '{name}' com especialidade: {specialty}.",
            ),
        ]
        changed = False
        for skill in defaults:
            if skill.id not in self._skills:
                self._skills[skill.id] = skill
                changed = True
        if changed:
            self._save()

    def register(self, skill: Skill) -> str:
        """Regista uma nova skill."""
        self._skills[skill.id] = skill
        self._save()
        logger.info(f"[SkillRegistry] Registada: {skill.id} v{skill.version}")
        return f"✅ Skill '{skill.name}' registada (id={skill.id})"

    def get(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def record_execution(self, skill_id: str, success: bool,
                         duration_s: float = 0.0, tokens: int = 0,
                         quality: float = -1.0) -> None:
        """Regista métricas de uma execução de skill."""
        if skill_id not in self._metrics:
            self._metrics[skill_id] = SkillMetrics(skill_id=skill_id)
        m = self._metrics[skill_id]
        if success:
            m.successes += 1
        else:
            m.failures += 1
        m.total_duration_s    += duration_s
        m.total_cost_tokens   += tokens
        m.last_used            = datetime.now().isoformat()
        if quality >= 0:
            m.quality_scores.append(quality)
            m.quality_scores = m.quality_scores[-50:]
        self._save_metrics()

    def best_for_category(self, category: str, top_n: int = 3) -> list[Skill]:
        """Retorna as melhores skills de uma categoria por composite_score."""
        candidates = [s for s in self._skills.values()
                      if s.category == category and s.enabled]
        scored = sorted(
            candidates,
            key=lambda s: self._metrics.get(s.id, SkillMetrics(s.id)).composite_score,
            reverse=True,
        )
        return scored[:top_n]

    def match_task(self, task_description: str) -> Optional[Skill]:
        """Encontra a skill mais adequada para uma descrição de tarefa."""
        task_lower = task_description.lower()
        category_keywords = {
            "research":  ["pesquis", "investig", "procur", "buscar", "encontrar", "web"],
            "coding":    ["implement", "codigo", "código", "programar", "funcao", "classe", "bug", "corrig"],
            "web":       ["site", "html", "página", "landing", "web", "deploy"],
            "analysis":  ["analisa", "revis", "audit", "melhora", "optimiz"],
            "writing":   ["documenta", "readme", "escreve", "changelog", "guia"],
            "system":    ["agente", "evolu", "sistema", "arquitectura", "ecossistema"],
        }
        scores = {}
        for cat, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > 0:
                scores[cat] = score

        if not scores:
            return self.get("code_implement")  # default

        best_cat = max(scores, key=scores.get)
        best_skills = self.best_for_category(best_cat, top_n=1)
        return best_skills[0] if best_skills else None

    def get_ranking(self) -> list[dict]:
        """Ranking completo de skills por composite_score."""
        result = []
        for sid, skill in self._skills.items():
            m = self._metrics.get(sid, SkillMetrics(sid))
            result.append({**skill.to_dict(), **m.to_dict()})
        return sorted(result, key=lambda x: x.get("composite_score", 0), reverse=True)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def _save(self):
        REGISTRY_FILE.write_text(
            json.dumps([s.to_dict() for s in self._skills.values()],
                       indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _save_metrics(self):
        METRICS_FILE.write_text(
            json.dumps([m.to_dict() for m in self._metrics.values()],
                       indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


# Instância global
_registry: Optional[SkillRegistry] = None

def get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
