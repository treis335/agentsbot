"""
dashboard/api/metrics_collector.py — Coleta métricas reais do ecossistema.

Alimenta o dashboard com dados vivos dos agentes, tarefas, memória e eventos.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class MetricsCollector:
    """Coleta métricas reais do ecossistema para o dashboard."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent

    def collect(self) -> Dict[str, Any]:
        """Coleta todas as métricas do sistema em tempo real."""
        return {
            "agents": self._get_agents_metrics(),
            "tasks": self._get_tasks_metrics(),
            "memory": self._get_memory_metrics(),
            "events": self._get_events_metrics(),
            "system": self._get_system_metrics(),
            "timestamp": datetime.now().isoformat(),
        }

    def _get_agents_metrics(self) -> Dict[str, Any]:
        """Métricas dos agentes registados."""
        agents_file = self.project_root / "agents" / "registry" / "agents.json"
        if not agents_file.exists():
            return {"total": 0, "online": 0, "by_role": {}, "names": []}

        with open(agents_file, "r", encoding="utf-8") as f:
            agents = json.load(f)

        by_role = {}
        names = []
        for a in agents:
            role = a.get("role", "unknown")
            by_role[role] = by_role.get(role, 0) + 1
            names.append(a.get("name", "?"))

        return {
            "total": len(agents),
            "online": len(agents),  # todos idle mas disponiveis
            "by_role": by_role,
            "names": names,
        }

    def _get_tasks_metrics(self) -> Dict[str, Any]:
        """Métricas do backlog de tarefas."""
        backlog_file = self.project_root / "memory" / "backlog.json"
        if not backlog_file.exists():
            return {"total": 0, "done": 0, "pending": 0, "running": 0, "failed": 0}

        with open(backlog_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        done = sum(1 for t in tasks if t.get("status") in ("done", "completed"))
        running = sum(1 for t in tasks if t.get("status") == "running")
        pending = sum(1 for t in tasks if t.get("status") in ("pending", "todo", "backlog"))
        failed = sum(1 for t in tasks if t.get("status") in ("failed", "error"))

        return {
            "total": len(tasks),
            "done": done,
            "running": running,
            "pending": pending,
            "failed": failed,
        }

    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Métricas dos sistemas de memória."""
        mem_dir = self.project_root / "memory"
        if not mem_dir.exists():
            return {}

        stats = {}
        # Episodic memory
        ep_file = mem_dir / "loop_episodes.json"
        if ep_file.exists():
            with open(ep_file, "r", encoding="utf-8") as f:
                episodes = json.load(f)
            stats["episodios"] = len(episodes) if isinstance(episodes, list) else 0

        # Semantic index
        si_file = mem_dir / "semantic_index.json"
        if si_file.exists():
            with open(si_file, "r", encoding="utf-8") as f:
                idx = json.load(f)
            stats["indice_semantico"] = len(idx) if isinstance(idx, list) else 0

        # Conversation
        conv_file = mem_dir / "conversation.jsonl"
        if conv_file.exists():
            with open(conv_file, "r", encoding="utf-8") as f:
                stats["conversas"] = sum(1 for _ in f)

        # Evolution log
        evo_file = mem_dir / "evolution_log.json"
        if evo_file.exists():
            with open(evo_file, "r", encoding="utf-8") as f:
                evo = json.load(f)
            stats["evolucoes"] = len(evo) if isinstance(evo, list) else 0

        # Autonomous log size
        auto_file = mem_dir / "autonomous_log.md"
        if auto_file.exists():
            stats["log_autonomo_bytes"] = auto_file.stat().st_size

        return stats

    def _get_events_metrics(self) -> Dict[str, Any]:
        """Métricas de eventos recentes."""
        hub_file = self.project_root / "_hub_data.json"
        if not hub_file.exists():
            return {"total": 0}

        with open(hub_file, "r", encoding="utf-8") as f:
            hub = json.load(f)

        total = hub.get("total_lines", 0)
        return {"total": total}

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Métricas do sistema (ciclos, uptime, etc)."""
        metrics = {}

        # Ciclo count
        ciclo_file = self.project_root / "memory" / "ciclo_count.txt"
        if ciclo_file.exists():
            with open(ciclo_file, "r") as f:
                try:
                    metrics["ciclo_atual"] = int(f.read().strip())
                except ValueError:
                    metrics["ciclo_atual"] = 0

        # Checkpoint
        cp_file = self.project_root / "memory" / "checkpoint.json"
        if cp_file.exists():
            with open(cp_file, "r", encoding="utf-8") as f:
                cp = json.load(f)
            metrics["ultimo_checkpoint"] = cp.get("task", "?")[:80]
            metrics["ultimo_checkpoint_time"] = cp.get("timestamp", "")

        # Session
        session_file = self.project_root / "memory" / ".session_id"
        if session_file.exists():
            with open(session_file, "r") as f:
                metrics["session_id"] = f.read().strip()[:12]

        return metrics
