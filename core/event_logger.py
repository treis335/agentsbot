"""
core/event_logger.py — Logging estruturado de eventos do ecossistema.

Regista tudo num formato JSONL com estrutura consistente:
  - execução de skill
  - reflexão
  - evolução
  - erro
  - promoção
  - rollback
  - diálogo entre agentes

Os eventos ficam em events/YYYY/MM/DD/events.jsonl
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

EVENTS_BASE = Path("events")
_lock = threading.Lock()


def _event_file() -> Path:
    now  = datetime.now()
    path = EVENTS_BASE / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path / "events.jsonl"


def log_event(
    event_type: str,
    agent: str = "system",
    data: Optional[dict] = None,
    success: Optional[bool] = None,
    duration_s: Optional[float] = None,
    tags: Optional[list] = None,
) -> None:
    """
    Regista um evento estruturado.

    Args:
        event_type: tipo do evento (skill_execution, reflection, evolution,
                    error, promotion, rollback, agent_dialogue, task_complete)
        agent:      agente que gerou o evento
        data:       dados adicionais do evento
        success:    True/False/None
        duration_s: duração em segundos
        tags:       tags para filtrar eventos
    """
    event = {
        "ts":         datetime.now().isoformat(),
        "type":       event_type,
        "agent":      agent,
        "success":    success,
        "duration_s": round(duration_s, 3) if duration_s is not None else None,
        "tags":       tags or [],
        "data":       data or {},
    }
    try:
        with _lock:
            with open(_event_file(), "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug(f"[EventLogger] Erro ao escrever evento: {e}")


def log_skill_execution(agent: str, skill_id: str, task: str,
                        success: bool, duration_s: float,
                        tokens: int = 0, result_preview: str = "") -> None:
    log_event(
        "skill_execution",
        agent=agent,
        success=success,
        duration_s=duration_s,
        data={
            "skill_id":       skill_id,
            "task_preview":   task[:100],
            "tokens":         tokens,
            "result_preview": result_preview[:200],
        },
        tags=["skill", skill_id],
    )


def log_reflection(agent: str, task: str, what_worked: str,
                   what_failed: str, new_skill: bool = False) -> None:
    log_event(
        "reflection",
        agent=agent,
        success=True,
        data={
            "task_preview":  task[:100],
            "what_worked":   what_worked[:200],
            "what_failed":   what_failed[:200],
            "new_skill":     new_skill,
        },
        tags=["reflection"],
    )


def log_evolution(description: str, files_changed: list,
                  success: bool, agent: str = "auto_evolver") -> None:
    log_event(
        "evolution",
        agent=agent,
        success=success,
        data={
            "description":   description[:200],
            "files_changed": files_changed[:10],
        },
        tags=["evolution"],
    )


def log_agent_dialogue(agents: list, topic: str,
                       decision: str, n_tasks: int) -> None:
    log_event(
        "agent_dialogue",
        agent="council",
        success=True,
        data={
            "agents":    agents,
            "topic":     topic[:150],
            "decision":  decision[:200],
            "n_tasks":   n_tasks,
        },
        tags=["dialogue", "council"],
    )


def log_error(agent: str, error: str, context: str = "") -> None:
    log_event(
        "error",
        agent=agent,
        success=False,
        data={
            "error":   error[:300],
            "context": context[:200],
        },
        tags=["error"],
    )


def log_promotion(what: str, from_version: str, to_version: str) -> None:
    log_event(
        "promotion",
        agent="governance",
        success=True,
        data={"what": what, "from": from_version, "to": to_version},
        tags=["promotion", "governance"],
    )


def log_rollback(what: str, reason: str) -> None:
    log_event(
        "rollback",
        agent="governance",
        success=True,
        data={"what": what, "reason": reason[:200]},
        tags=["rollback", "governance"],
    )


def get_recent_events(n: int = 50, event_type: Optional[str] = None,
                      tag: Optional[str] = None) -> list[dict]:
    """Lê os N eventos mais recentes, com filtro opcional."""
    results = []
    try:
        f = _event_file()
        if not f.exists():
            return []
        lines = f.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
                if event_type and ev.get("type") != event_type:
                    continue
                if tag and tag not in ev.get("tags", []):
                    continue
                results.append(ev)
                if len(results) >= n:
                    break
            except Exception:
                pass
    except Exception:
        pass
    return list(reversed(results))


def get_daily_stats() -> dict:
    """Estatísticas do dia actual."""
    events = get_recent_events(n=1000)
    stats = {
        "total":      len(events),
        "successes":  sum(1 for e in events if e.get("success") is True),
        "failures":   sum(1 for e in events if e.get("success") is False),
        "by_type":    {},
        "by_agent":   {},
    }
    for ev in events:
        t = ev.get("type", "unknown")
        a = ev.get("agent", "unknown")
        stats["by_type"][t]  = stats["by_type"].get(t, 0) + 1
        stats["by_agent"][a] = stats["by_agent"].get(a, 0) + 1
    return stats
