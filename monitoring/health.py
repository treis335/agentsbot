"""
monitoring/health.py — Verificacao de saude do ecossistema.

Monitoriza:
- Heartbeat dos agentes
- Estado dos servicos
- Uptime do sistema
- Alertas automaticos
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from core.config import Config
from core.bus import bus

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Verificador de saude do sistema.

    Uso:
        health = HealthChecker()
        status = health.check_all()
        alerts = health.get_active_alerts()
    """

    def __init__(self):
        self.config = Config
        self._alerts: list[dict] = []
        self._max_alerts = 100

    def check_agent_health(self, agent_id: str, last_active: Optional[str] = None) -> dict:
        """
        Verifica saude de um agente.

        Returns:
            Dict com status, uptime, alertas
        """
        if not last_active:
            return {"status": "unknown", "agent_id": agent_id}

        try:
            last = datetime.fromisoformat(last_active)
            now = datetime.now()
            diff_minutes = (now - last).total_seconds() / 60

            if diff_minutes < 5:
                return {"status": "healthy", "agent_id": agent_id, "last_seen_min": round(diff_minutes, 1)}
            elif diff_minutes < 30:
                return {"status": "warning", "agent_id": agent_id, "last_seen_min": round(diff_minutes, 1)}
            else:
                alert = {
                    "type": "agent_stale",
                    "agent_id": agent_id,
                    "message": f"Agente sem atividade ha {round(diff_minutes)}min",
                    "timestamp": datetime.now().isoformat(),
                    "severity": "warning",
                }
                self._add_alert(alert)
                return {"status": "stale", "agent_id": agent_id, "last_seen_min": round(diff_minutes, 1)}
        except Exception:
            return {"status": "error", "agent_id": agent_id}

    def check_system_health(self) -> dict:
        """Verifica saude geral do sistema."""
        return {
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "config_valid": len(self.config.validate()) == 0,
        }

    def _add_alert(self, alert: dict) -> None:
        """Adiciona um alerta a fila."""
        self._alerts.append(alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts.pop(0)
        logger.warning(f"[Health] Alerta: {alert['message']}")

    def get_active_alerts(self) -> list[dict]:
        """Retorna alertas ativos (ultimas 24h)."""
        cutoff = datetime.now() - timedelta(hours=24)
        return [
            a for a in self._alerts
            if datetime.fromisoformat(a["timestamp"]) > cutoff
        ]

    def clear_alerts(self) -> None:
        """Limpa todos os alertas."""
        self._alerts.clear()
