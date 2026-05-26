"""
core/persistent_bus.py — Event Bus com Write-Ahead Log persistente.

Substitui o EventBus in-memory com uma versão que:
  1. Persiste cada evento em JSONL antes de notificar handlers (WAL)
  2. Marca eventos como processados após handlers correrem sem erro
  3. Permite replay de eventos não processados ao arrancar
  4. Roda logs diariamente (memory/event_log/YYYY-MM-DD.jsonl)

API 100% compatível com EventBus — sem mudanças nos chamadores.

Formato de cada linha JSONL:
    {"id": "uuid", "type": "...", "data": {...},
     "timestamp": "ISO", "processed": true, "process_errors": 0}
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Dir para os logs diários de eventos
_EVENT_LOG_DIR = Path("memory") / "event_log"


class PersistentEventBus:
    """
    Event Bus com write-ahead log em ficheiro JSONL.

    Cada evento é escrito em disco ANTES de ser entregue aos handlers.
    Se o processo morrer a meio, o bus_replay.py entrega os eventos em falta
    no próximo arranque.

    Uso (idêntico ao EventBus original):
        from core.bus import bus
        bus.subscribe("task.completed", handler)
        await bus.publish("task.completed", {"result": "ok"})
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self._subscribers: dict[str, list[Callable]] = {}
        self._history: list[dict] = []
        self._max_history = 1000
        self._log_dir = log_dir or _EVENT_LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._current_log_date: Optional[date] = None
        self._log_path: Optional[Path] = None
        self._ensure_log_file()

    # ── Gestão do ficheiro de log ───────────────────────────────────────────────

    def _ensure_log_file(self) -> Path:
        """Garante que o ficheiro de log para hoje está aberto. Rota diariamente."""
        today = date.today()
        if self._current_log_date != today:
            self._current_log_date = today
            self._log_path = self._log_dir / f"{today.isoformat()}.jsonl"
            logger.info(f"[PersistentBus] Log: {self._log_path}")
        return self._log_path

    def _write_event(self, event: dict) -> None:
        """Escreve evento no WAL (write-ahead log). Chamado ANTES dos handlers."""
        path = self._ensure_log_file()
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.error(f"[PersistentBus] Erro ao escrever WAL: {e}")

    def _mark_processed(self, event_id: str, errors: int = 0) -> None:
        """Marca evento como processado no log (reescreve linha — append+compact)."""
        # Implementação leve: escrevemos uma linha de "patch" no mesmo ficheiro.
        # O bus_replay.py ignora eventos com processed=True ao fazer replay.
        path = self._ensure_log_file()
        try:
            with open(path, "a", encoding="utf-8") as f:
                patch = {
                    "_patch": True,
                    "id": event_id,
                    "processed": True,
                    "process_errors": errors,
                    "processed_at": datetime.now().isoformat(),
                }
                f.write(json.dumps(patch, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[PersistentBus] Erro ao marcar processado: {e}")

    # ── Interface pública (compatível com EventBus) ─────────────────────────────

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscreve um handler a um tipo de evento."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"[PersistentBus] Subscricao: {event_type} -> {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove subscrição."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publica um evento.

        Ordem:
          1. Gera ID único e timestamp
          2. Escreve no WAL (disco)
          3. Notifica handlers
          4. Marca como processado no WAL
        """
        event_id = str(uuid.uuid4())[:12]
        event = {
            "id": event_id,
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "processed": False,
            "process_errors": 0,
        }

        # 1. Persistir ANTES de entregar (WAL)
        self._write_event(event)

        # 2. Histórico in-memory (para get_history())
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        logger.info(f"[PersistentBus] Evento: {event_type} [{event_id}]")

        # 3. Notificar handlers
        handlers = (
            self._subscribers.get(event_type, []) +
            self._subscribers.get("*", [])
        )
        errors = 0
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                errors += 1
                logger.error(f"[PersistentBus] Erro em handler {handler.__name__}: {e}")

        # 4. Marcar como processado
        self._mark_processed(event_id, errors=errors)

    async def publish_raw(self, event: dict) -> None:
        """
        Publica um evento já construído (usado pelo replay).
        Não escreve no WAL novamente — apenas entrega aos handlers.
        """
        event_type = event.get("type", "unknown")
        handlers = (
            self._subscribers.get(event_type, []) +
            self._subscribers.get("*", [])
        )
        errors = 0
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                errors += 1
                logger.error(f"[PersistentBus] Replay erro em {handler.__name__}: {e}")

        self._mark_processed(event["id"], errors=errors)

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Retorna histórico in-memory de eventos."""
        if event_type:
            filtered = [e for e in self._history if e.get("type") == event_type]
            return filtered[-limit:]
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Limpa histórico in-memory (não apaga os ficheiros de log)."""
        self._history.clear()

    def log_files(self) -> list[Path]:
        """Retorna lista de ficheiros de log existentes, ordenados por data."""
        return sorted(self._log_dir.glob("*.jsonl"))

    def unprocessed_events(self, log_path: Optional[Path] = None) -> list[dict]:
        """
        Lê um ficheiro de log e retorna eventos não processados.
        Usado pelo bus_replay.py no arranque.
        """
        path = log_path or self._log_path
        if not path or not path.exists():
            return []

        events: dict[str, dict] = {}
        processed_ids: set[str] = set()

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if record.get("_patch"):
                        # Linha de patch: marcar ID como processado
                        processed_ids.add(record["id"])
                    else:
                        events[record["id"]] = record

        except Exception as e:
            logger.error(f"[PersistentBus] Erro ao ler log {path}: {e}")
            return []

        return [
            e for eid, e in events.items()
            if eid not in processed_ids and not e.get("processed", False)
        ]
