"""
agents/collaboration/knowledge_base.py — Base de conhecimento partilhada.

Qualquer agente pode:
  - Adicionar conhecimento: aprendizagens, padrões, soluções
  - Consultar conhecimento relevante para uma tarefa
  - Ver o que outros agentes descobriram

O conhecimento é categorizado por tipo e indexado por palavras-chave
para recuperação rápida sem API.

Persiste em memory/knowledge_base.json
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KB_FILE = Path("memory") / "knowledge_base.json"
_MAX_ENTRIES = 500


class KnowledgeType:
    SOLUTION    = "solution"      # solução para problema específico
    PATTERN     = "pattern"       # padrão reutilizável
    WARNING     = "warning"       # aviso sobre algo perigoso
    DISCOVERY   = "discovery"     # descoberta interessante
    BEST_PRACTICE = "best_practice"  # boa prática confirmada
    AGENT_SKILL = "agent_skill"   # capacidade de agente específico


@dataclass
class KnowledgeEntry:
    agent:      str           # quem descobriu
    k_type:     str           # KnowledgeType.*
    title:      str           # título curto
    content:    str           # conteúdo
    keywords:   list[str] = field(default_factory=list)
    confidence: int = 7       # 1-10: quão confiante está o agente
    uses:       int = 0       # vezes que foi consultado
    k_id:       str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
    timestamp:  str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def matches(self, query: str) -> float:
        """Score de relevância para uma query (Jaccard simples)."""
        query_words = set(query.lower().split())
        kw_words = set(" ".join(self.keywords).lower().split())
        title_words = set(self.title.lower().split())
        content_words = set(self.content.lower().split())
        all_words = kw_words | title_words | content_words
        if not query_words or not all_words:
            return 0.0
        return len(query_words & all_words) / len(query_words | all_words)

    def to_prompt_line(self) -> str:
        icon = {"solution": "💡", "pattern": "🔄", "warning": "⚠️",
                "discovery": "🔍", "best_practice": "✅", "agent_skill": "🤖"}.get(self.k_type, "📝")
        return f"{icon} [{self.agent}] {self.title}: {self.content[:150]}"


class KnowledgeBase:
    """Base de conhecimento partilhada entre todos os agentes."""

    def __init__(self):
        self._entries: list[KnowledgeEntry] = self._load()

    def _load(self) -> list[KnowledgeEntry]:
        try:
            if _KB_FILE.exists():
                data = json.loads(_KB_FILE.read_text(encoding="utf-8"))
                return [KnowledgeEntry(**{
                    k: v for k, v in d.items()
                    if k in KnowledgeEntry.__dataclass_fields__
                }) for d in data]
        except Exception:
            pass
        return []

    def _save(self) -> None:
        _KB_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._entries[-_MAX_ENTRIES:]]
        _KB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(
        self,
        agent: str,
        k_type: str,
        title: str,
        content: str,
        keywords: list[str] = None,
        confidence: int = 7,
    ) -> str:
        """Adiciona entrada de conhecimento. Retorna k_id."""
        # Evitar duplicados (mesmo título do mesmo agente)
        for e in self._entries:
            if e.agent == agent and e.title.lower() == title.lower():
                # Actualizar em vez de duplicar
                e.content = content
                e.timestamp = datetime.now().isoformat()
                self._save()
                return e.k_id

        entry = KnowledgeEntry(
            agent=agent,
            k_type=k_type,
            title=title,
            content=content,
            keywords=keywords or self._auto_keywords(title + " " + content),
            confidence=confidence,
        )
        self._entries.append(entry)
        self._save()
        logger.debug(f"[KB] Novo conhecimento de {agent}: {title[:50]}")
        return entry.k_id

    def _auto_keywords(self, text: str) -> list[str]:
        """Extrai keywords automáticas do texto."""
        stop_words = {"de", "o", "a", "os", "as", "e", "é", "em", "para", "com",
                     "que", "um", "uma", "por", "do", "da", "dos", "das", "no", "na",
                     "se", "ao", "sua", "seu", "the", "is", "to", "of", "and", "in"}
        words = [w.lower().strip(".,!?:;()[]") for w in text.split()]
        return list({w for w in words if len(w) > 3 and w not in stop_words})[:10]

    def query(self, query: str, limit: int = 5, min_score: float = 0.1) -> list[KnowledgeEntry]:
        """Busca entradas relevantes para uma query."""
        scored = [(e.matches(query), e) for e in self._entries]
        scored = [(s, e) for s, e in scored if s >= min_score]
        scored.sort(key=lambda x: (-x[0], -x[1].confidence))

        results = [e for _, e in scored[:limit]]
        # Incrementar contador de uso
        for e in results:
            e.uses += 1
        if results:
            self._save()
        return results

    def get_prompt_context(self, query: str, max_chars: int = 1000) -> str:
        """Retorna contexto de conhecimento para prompt."""
        entries = self.query(query, limit=4)
        if not entries:
            return ""
        lines = ["\n## CONHECIMENTO PARTILHADO DA EQUIPA"]
        total = 0
        for e in entries:
            line = e.to_prompt_line()
            total += len(line)
            if total > max_chars:
                break
            lines.append(line)
        return "\n".join(lines) + "\n"

    def get_by_agent(self, agent: str) -> list[KnowledgeEntry]:
        """Tudo o que um agente específico partilhou."""
        return [e for e in self._entries if e.agent == agent]

    def top_contributors(self, limit: int = 5) -> list[dict]:
        """Agentes que mais conhecimento partilharam."""
        counts: dict[str, int] = {}
        for e in self._entries:
            counts[e.agent] = counts.get(e.agent, 0) + 1
        return sorted(
            [{"agent": k, "entries": v} for k, v in counts.items()],
            key=lambda x: -x["entries"]
        )[:limit]

    def stats(self) -> dict:
        return {
            "total_entries": len(self._entries),
            "by_type": {t: sum(1 for e in self._entries if e.k_type == t)
                       for t in [KnowledgeType.SOLUTION, KnowledgeType.PATTERN,
                                 KnowledgeType.WARNING, KnowledgeType.BEST_PRACTICE]},
            "top_contributors": self.top_contributors(3),
            "most_used": sorted(
                [{"title": e.title, "uses": e.uses, "agent": e.agent}
                 for e in self._entries if e.uses > 0],
                key=lambda x: -x["uses"]
            )[:5],
        }


# Singleton
_kb: Optional[KnowledgeBase] = None

def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
