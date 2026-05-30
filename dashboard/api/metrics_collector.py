"""dashboard/api/metrics_collector.py - Coleta metricas reais do ecossistema."""
import json, os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class MetricsCollector:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent

    def collect(self) -> Dict[str, Any]:
        return {
            "agents": self._get_agents_metrics(),
            "tasks": self._get_tasks_metrics(),
            "memory": self._get_memory_metrics(),
            "events": self._get_events_metrics(),
            "system": self._get_system_metrics(),
            "timestamp": datetime.now().isoformat(),
        }

    def _get_agents_metrics(self) -> Dict[str, Any]:
        agents_file = self.project_root / "agents" / "registry" / "agents.json"
        if not agents_file.exists():
            agents_file = self.project_root / "agents.json"
        if not agents_file.exists():
            return {"total": 0, "online": 0, "by_role": {}, "names": []}
        with open(agents_file, "r", encoding="utf-8") as f:
            agents = json.load(f)
        by_role = {}
        names = []
        for a in agents:
            role = a.get("role", a.get("name", "unknown"))
            by_role[role] = by_role.get(role, 0) + 1
            names.append(a.get("name", "?"))
        return {"total": len(agents), "online": len(agents), "by_role": by_role, "names": names}

    def _get_tasks_metrics(self) -> Dict[str, Any]:
        backlog_file = self.project_root / "memory" / "backlog.json"
        if not backlog_file.exists():
            return {"total": 0, "done": 0, "pending": 0, "running": 0, "failed": 0}
        with open(backlog_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        done = sum(1 for t in tasks if t.get("status") in ("done", "completed"))
        running = sum(1 for t in tasks if t.get("status") == "running")
        pending = sum(1 for t in tasks if t.get("status") in ("pending", "todo", "backlog"))
        failed = sum(1 for t in tasks if t.get("status") in ("failed", "error"))
        return {"total": len(tasks), "done": done, "running": running, "pending": pending, "failed": failed}

    def _get_memory_metrics(self) -> Dict[str, Any]:
        ep_file = self.project_root / "memory" / "loop_episodes.json"
        if not ep_file.exists():
            return {"episodes": 0, "agents_activity": {}}
        with open(ep_file, "r", encoding="utf-8") as f:
            episodes = json.load(f)
        agents_activity = {}
        for ep in episodes:
            agent = ep.get("agent", "unknown")
            agents_activity[agent] = agents_activity.get(agent, 0) + 1
        return {"episodes": len(episodes), "agents_activity": agents_activity}

    def _get_events_metrics(self) -> Dict[str, Any]:
        evo_file = self.project_root / "memory" / "evolution_log.json"
        if not evo_file.exists():
            return {"total": 0, "by_type": {}}
        with open(evo_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        by_type = {}
        for ev in events:
            t = ev.get("tipo", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {"total": len(events), "by_type": by_type}

    def _get_system_metrics(self) -> Dict[str, Any]:
        return {"status": "online", "uptime": "active"}
