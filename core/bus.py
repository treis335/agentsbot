"""
core/bus.py — Event Bus interno para comunicacao entre agentes.

Permite que agentes publiquem eventos e subscrevam eventos
de outros agentes, sem dependencia direta.
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import Callable, Awaitable, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class EventBus:
    """
    Barramento de eventos assincrono.

    Uso:
        bus = EventBus()
        bus.subscribe("task.completed", meu_handler)
        await bus.publish("task.completed", {"task_id": "123", "result": "ok"})
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._history: list[dict] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscreve um handler a um tipo de evento."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"[EventBus] Subscricao: {event_type} -> {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove subscricao."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publica um evento para todos os subscritores.

        Args:
            event_type: Tipo do evento (ex: "agent.started", "task.completed")
            data: Dados do evento (dict, string, etc.)
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        # Guardar historico
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        logger.info(f"[EventBus] Evento: {event_type}")

        # Notificar subscritores
        handlers = self._subscribers.get(event_type, []) + self._subscribers.get("*", [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"[EventBus] Erro em handler {handler.__name__}: {e}")

    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[dict]:
        """Retorna historico de eventos, opcionalmente filtrado."""
        if event_type:
            filtered = [e for e in self._history if e["type"] == event_type]
            return filtered[-limit:]
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Limpa historico de eventos."""
        self._history.clear()


# Instancia global do barramento
bus = EventBus()
