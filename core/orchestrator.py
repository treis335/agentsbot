"""
core/orchestrator.py — Orquestrador central do ecossistema.

Coordena:
- Ciclo de vida dos agentes
- Distribuicao de tarefas
- Pipeline multi-agente
- Heartbeat e monitorizacao
- Auto-recuperacao
"""
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config
from .bus import bus, EventBus

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestrador principal.

    Uso:
        orch = Orchestrator()
        await orch.start()
        # ... sistema corre ...
        await orch.shutdown()
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.config = Config
        self.bus = event_bus or bus
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}
        self._start_time: float = 0.0
        self._cycle_count: int = 0

        # Subscrever eventos do sistema
        self.bus.subscribe("system.shutdown", self._on_shutdown)

    async def start(self) -> None:
        """Inicia o orquestrador e todos os subsistemas."""
        self._running = True
        self._start_time = time.time()

        # Validar config
        warnings = self.config.validate()
        for w in warnings:
            logger.warning(f"[Orchestrator] Config warning: {w}")

        logger.info("=" * 60)
        logger.info("  CORREOTO ECOSYSTEM v2.0")
        logger.info(f"  Repo: {self.config.GITHUB_REPO}")
        logger.info(f"  Path: {self.config.REPO_LOCAL_PATH}")
        logger.info(f"  Inicio: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        await self.bus.publish("system.started", {
            "version": "2.0",
            "timestamp": datetime.now().isoformat(),
        })

    async def shutdown(self) -> None:
        """Para todos os subsistemas ordenadamente."""
        logger.info("[Orchestrator] A encerrar...")
        self._running = False

        # Cancelar todas as tarefas
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"[Orchestrator] Tarefa cancelada: {name}")

        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        await self.bus.publish("system.stopped", {
            "uptime": round(time.time() - self._start_time, 1),
            "cycles": self._cycle_count,
        })
        logger.info("[Orchestrator] Sistema encerrado.")

    async def _on_shutdown(self, event: dict) -> None:
        """Handler para evento de shutdown."""
        await self.shutdown()

    @property
    def uptime(self) -> float:
        """Tempo de atividade em segundos."""
        return time.time() - self._start_time if self._start_time else 0

    @property
    def is_running(self) -> bool:
        return self._running
