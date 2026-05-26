"""
memory/episodica.py — Memoria episodica (experiencias passadas).

Cada agente tem a sua propria memoria episodica que regista:
- Interaccoes com ferramentas
- Erros e sucessos
- Contexto de execucao
- Decisoes tomadas

Isto permite que os agentes aprendam com a experiencia.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """
    Memoria episodica de um agente.

    Estrutura:
    [
        {
            "episode": {
                "action": "write_file",
                "args": {...},
                "result": "sucesso/erro",
                "context": "O que estava a acontecer",
            },
            "timestamp": "...",
            "success": True/False,
            "lesson": "O que aprendi",
        },
        ...
    ]
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.config = Config
        self.memory_dir = self.config.MEMORY_DIR / "episodica"
        self.memory_file = self.memory_dir / f"{agent_id}.json"
        self._episodes: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if not self.memory_file.exists():
            return []
        try:
            return json.loads(self.memory_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        # Manter apenas os ultimos 100 episodios
        data = self._episodes[-100:]
        self.memory_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def record(self, action: str, args: dict, result: str,
               success: bool, context: str = "", lesson: str = "") -> None:
        """Regista um episodio (experiencia)."""
        self._episodes.append({
            "episode": {
                "action": action,
                "args": args,
                "result": str(result)[:500],
                "context": context,
            },
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "lesson": lesson,
        })
        self._save()

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Retorna episodios recentes."""
        return self._episodes[-limit:]

    def get_failures(self, limit: int = 10) -> list[dict]:
        """Retorna episodios com falhas."""
        failures = [e for e in self._episodes if not e["success"]]
        return failures[-limit:]

    def get_successes(self, limit: int = 10) -> list[dict]:
        """Retorna episodios com sucesso."""
        successes = [e for e in self._episodes if e["success"]]
        return successes[-limit:]

    def get_lessons(self, limit: int = 10) -> list[str]:
        """Retorna licoes aprendidas."""
        lessons = [e["lesson"] for e in self._episodes if e.get("lesson")]
        return lessons[-limit:]


    def get_similar_failures(self, task: str, limit: int = 3) -> list[dict]:
        """
        Retorna falhas similares à tarefa atual (matching local por palavras).
        Delega para FailureMemory se disponível, senão usa episódios internos.
        """
        try:
            from memory.failure_memory import FailureMemory
            fm = FailureMemory(self.agent_id)
            return fm.get_similar_failures(task, limit=limit)
        except Exception:
            # Fallback: usar episódios internos
            task_words = set(task.lower().split())
            failures = [e for e in self._episodes if not e.get("success", True)]
            scored = []
            for ep in failures:
                ctx = ep.get("episode", {}).get("context", "").lower()
                common = task_words & set(ctx.split())
                if common:
                    scored.append((len(common), ep))
            scored.sort(reverse=True)
            return [ep for _, ep in scored[:limit]]
    def clear(self) -> None:
        """Limpa memoria episodica."""
        self._episodes = []
        self._save()
