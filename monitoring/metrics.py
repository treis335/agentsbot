"""
monitoring/metrics.py — Coleta de metricas do ecossistema.

Inspirado no Cost Tracking do Mission Control:
- Tokens gastos por agente/modelo
- Tool calls por tipo
- Tempo de execucao
- Erros e taxa de sucesso
- Latencia p50/p95/p99
"""
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Coletor de metricas do sistema.

    Uso:
        metrics = MetricsCollector()
        metrics.track_tool_call("developer", "write_file", 1.2, True)
        metrics.track_token_usage("developer", "deepseek-chat", 150, 50)
        report = metrics.get_report()
    """

    def __init__(self):
        self.config = Config
        self.metrics_file = self.config.MONITORING_DIR / "metrics" / "metrics.json"
        self._data: dict = self._load()

    def _load(self) -> dict:
        if not self.metrics_file.exists():
            return self._default()
        try:
            return json.loads(self.metrics_file.read_text(encoding="utf-8"))
        except Exception:
            return self._default()

    def _save(self) -> None:
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _default(self) -> dict:
        return {
            "tool_calls": {
                "total": 0,
                "by_tool": {},
                "by_agent": {},
                "latencies": [],
            },
            "token_usage": {
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "by_model": {},
                "by_agent": {},
            },
            "errors": {
                "total": 0,
                "by_type": {},
            },
            "uptime": {
                "start_time": datetime.now().isoformat(),
                "total_seconds": 0,
            },
        }

    def track_tool_call(self, agent: str, tool: str, latency_ms: float, success: bool) -> None:
        """Regista uma chamada de ferramenta."""
        d = self._data
        d["tool_calls"]["total"] += 1

        # Por ferramenta
        if tool not in d["tool_calls"]["by_tool"]:
            d["tool_calls"]["by_tool"][tool] = {"count": 0, "errors": 0}
        d["tool_calls"]["by_tool"][tool]["count"] += 1
        if not success:
            d["tool_calls"]["by_tool"][tool]["errors"] += 1

        # Por agente
        if agent not in d["tool_calls"]["by_agent"]:
            d["tool_calls"]["by_agent"][agent] = {"count": 0, "errors": 0}
        d["tool_calls"]["by_agent"][agent]["count"] += 1
        if not success:
            d["tool_calls"]["by_agent"][agent]["errors"] += 1

        # Latencia (manter ultimas 1000)
        d["tool_calls"]["latencies"].append(latency_ms)
        if len(d["tool_calls"]["latencies"]) > 1000:
            d["tool_calls"]["latencies"] = d["tool_calls"]["latencies"][-1000:]

        self._save()

    def track_token_usage(self, agent: str, model: str,
                          prompt_tokens: int, completion_tokens: int) -> None:
        """Regista uso de tokens."""
        d = self._data
        d["token_usage"]["total_prompt_tokens"] += prompt_tokens
        d["token_usage"]["total_completion_tokens"] += completion_tokens

        # Por modelo
        if model not in d["token_usage"]["by_model"]:
            d["token_usage"]["by_model"][model] = {"prompt": 0, "completion": 0}
        d["token_usage"]["by_model"][model]["prompt"] += prompt_tokens
        d["token_usage"]["by_model"][model]["completion"] += completion_tokens

        # Por agente
        if agent not in d["token_usage"]["by_agent"]:
            d["token_usage"]["by_agent"][agent] = {"prompt": 0, "completion": 0}
        d["token_usage"]["by_agent"][agent]["prompt"] += prompt_tokens
        d["token_usage"]["by_agent"][agent]["completion"] += completion_tokens

        self._save()

    def track_error(self, error_type: str, agent: str = "system") -> None:
        """Regista um erro."""
        d = self._data
        d["errors"]["total"] += 1
        if error_type not in d["errors"]["by_type"]:
            d["errors"]["by_type"][error_type] = 0
        d["errors"]["by_type"][error_type] += 1
        self._save()

    def get_latency_stats(self) -> dict:
        """Calcula estatisticas de latencia (p50, p95, p99)."""
        latencies = sorted(self._data["tool_calls"]["latencies"])
        if not latencies:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0}

        n = len(latencies)
        return {
            "p50": latencies[int(n * 0.5)],
            "p95": latencies[int(n * 0.95)],
            "p99": latencies[int(n * 0.99)],
            "avg": sum(latencies) / n,
            "total_calls": n,
        }

    def get_report(self) -> dict:
        """Gera relatorio completo de metricas."""
        return {
            "tool_calls": {
                "total": self._data["tool_calls"]["total"],
                "by_tool": self._data["tool_calls"]["by_tool"],
                "latency": self.get_latency_stats(),
            },
            "token_usage": {
                "total_prompt": self._data["token_usage"]["total_prompt_tokens"],
                "total_completion": self._data["token_usage"]["total_completion_tokens"],
                "total": (self._data["token_usage"]["total_prompt_tokens"] +
                          self._data["token_usage"]["total_completion_tokens"]),
                "by_model": self._data["token_usage"]["by_model"],
            },
            "errors": self._data["errors"],
            "success_rate": self._calculate_success_rate(),
        }

    def _calculate_success_rate(self) -> float:
        """Calcula taxa de sucesso (0-100%)."""
        total = self._data["tool_calls"]["total"]
        if total == 0:
            return 100.0
        errors = self._data["errors"]["total"]
        return round((1 - errors / total) * 100, 1)
