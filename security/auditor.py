"""
security/auditor.py — Auditoria de todas as acoes do sistema.

Regista:
- Tool calls (quem, quando, que ferramenta, argumentos)
- Decisoes importantes
- Erros e excecoes
- Acessos a ficheiros sensiveis
- Commits e pushes
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Logger de auditoria.

    Uso:
        audit = AuditLogger()
        audit.log("tool_call", agent="developer", tool="write_file", args={"path": "..."})
        audit.log("decision", agent="supervisor", decision="Refatorar modulo X")
    """

    def __init__(self):
        self.config = Config
        self.audit_file = self.config.AUDIT_LOG
        self._entries: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if not self.audit_file.exists():
            return []
        try:
            return json.loads(self.audit_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self) -> None:
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        # Manter apenas ultimas 1000 entradas
        data = self._entries[-1000:]
        self.audit_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def log(self, event_type: str, **kwargs) -> None:
        """
        Regista um evento de auditoria.

        Args:
            event_type: Tipo de evento (tool_call, decision, error, access, commit)
            **kwargs: Detalhes do evento (agent, tool, args, result, etc.)
        """
        entry = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        # Sanitizar argumentos (remover conteudos muito grandes)
        if "args" in entry and isinstance(entry["args"], dict):
            entry["args"] = {k: str(v)[:200] for k, v in entry["args"].items()}
        if "result" in entry:
            entry["result"] = str(entry["result"])[:500]

        self._entries.append(entry)
        self._save()
        logger.debug(f"[Audit] {event_type}: {kwargs.get('agent', 'system')}")

    def get_logs(self, event_type: Optional[str] = None,
                 agent: Optional[str] = None,
                 limit: int = 50) -> list[dict]:
        """Consulta logs de auditoria com filtros."""
        entries = self._entries
        if event_type:
            entries = [e for e in entries if e["type"] == event_type]
        if agent:
            entries = [e for e in entries if e.get("agent") == agent]
        return entries[-limit:]

    def get_stats(self) -> dict:
        """Estatisticas de auditoria."""
        total = len(self._entries)
        by_type = {}
        for e in self._entries:
            t = e["type"]
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_entries": total,
            "by_type": by_type,
            "last_entry": self._entries[-1] if self._entries else None,
        }

    def clear(self) -> None:
        """Limpa logs de auditoria."""
        self._entries = []
        self._save()
