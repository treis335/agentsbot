"""
monitoring/agent_trace.py — Trace completo de cada execução de agente.

Regista, por cada run:
  - Todos os tool calls com args, resultado e duração
  - Tokens usados (prompt + completion)
  - Tempo total de execução
  - Custo estimado em USD (tokens × preço do modelo)
  - Resultado final (sucesso/falha)

Persiste em monitoring/traces/YYYY-MM-DD.jsonl
Exposto via /api/traces

Uso:
    trace = AgentTrace.start("developer", "task-123", "Corrigir bug X")
    trace.add_tool_call("write_file", {"path": "x.py"}, "ok", 120.5)
    trace.finish(success=True, result="Bug corrigido", tokens_in=400, tokens_out=200)
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_TRACES_DIR = Path("monitoring") / "traces"

# Preço por 1000 tokens em USD (input + output médio)
_MODEL_PRICES: dict[str, float] = {
    "deepseek-chat":     0.00027,   # ~$0.27/M tokens
    "deepseek-reasoner": 0.00055,
    "qwen2.5-coder:7b":  0.0,       # local — gratuito
    "qwen2.5-coder:14b": 0.0,
    "llama3.2:3b":       0.0,
    "mistral:7b":        0.0,
}
_DEFAULT_PRICE = 0.00027  # fallback para modelos desconhecidos


@dataclass
class ToolCallRecord:
    tool: str
    args: dict
    result: str
    latency_ms: float
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentTrace:
    """Trace de uma execução de agente."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    agent_name: str = ""
    task_id: str = ""
    task_description: str = ""
    model: str = "deepseek-chat"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = ""
    duration_ms: float = 0.0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    success: bool = False
    result_summary: str = ""
    error: str = ""
    _start_time: float = field(default_factory=time.time, repr=False)

    # -- Factory ----------------------------------------------------------------

    @classmethod
    def start(
        cls,
        agent_name: str,
        task_id: str,
        task_description: str,
        model: str = "deepseek-chat",
    ) -> "AgentTrace":
        trace = cls(
            agent_name=agent_name,
            task_id=task_id,
            task_description=task_description[:200],
            model=model,
        )
        logger.debug(f"[Trace] Iniciado: {trace.trace_id} agent={agent_name}")
        return trace

    # -- Registo de eventos -----------------------------------------------------

    def add_tool_call(
        self,
        tool: str,
        args: dict,
        result: str,
        latency_ms: float,
        success: bool = True,
    ) -> None:
        self.tool_calls.append(ToolCallRecord(
            tool=tool,
            args={k: str(v)[:100] for k, v in args.items()},  # truncar args grandes
            result=str(result)[:300],
            latency_ms=round(latency_ms, 1),
            success=success,
        ))

    def finish(
        self,
        success: bool,
        result: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        error: str = "",
    ) -> None:
        self.finished_at = datetime.now().isoformat()
        self.duration_ms = round((time.time() - self._start_time) * 1000, 1)
        self.success = success
        self.result_summary = str(result)[:300]
        self.error = str(error)[:300]
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out

        # Custo estimado
        price = _MODEL_PRICES.get(self.model, _DEFAULT_PRICE)
        total_tokens = tokens_in + tokens_out
        self.cost_usd = round(price * total_tokens / 1000, 6)

        # Persistir
        self._save()
        logger.debug(
            f"[Trace] Terminado: {self.trace_id} "
            f"success={success} tokens={total_tokens} cost=${self.cost_usd:.5f}"
        )

    # -- Persistência -----------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "model": self.model,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_call_count": len(self.tool_calls),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tokens_total": self.tokens_in + self.tokens_out,
            "cost_usd": self.cost_usd,
            "success": self.success,
            "result_summary": self.result_summary,
            "error": self.error,
        }

    def _save(self) -> None:
        _TRACES_DIR.mkdir(parents=True, exist_ok=True)
        log_path = _TRACES_DIR / f"{date.today().isoformat()}.jsonl"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(self.to_dict(), ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.error(f"[Trace] Erro ao guardar trace: {e}")


# -- Leitura de traces ----------------------------------------------------------

def load_traces(
    days: int = 1,
    agent_name: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """
    Carrega traces dos últimos N dias.
    Opcionalmente filtra por agente.
    """
    traces = []
    today = date.today()

    for i in range(days):
        target = today.replace(day=today.day - i) if today.day > i else today
        log_path = _TRACES_DIR / f"{target.isoformat()}.jsonl"
        if not log_path.exists():
            continue
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        t = json.loads(line)
                        if agent_name and t.get("agent_name") != agent_name:
                            continue
                        traces.append(t)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    # Mais recentes primeiro
    traces.sort(key=lambda t: t.get("started_at", ""), reverse=True)
    return traces[:limit]


def cost_summary(days: int = 1) -> dict:
    """
    Resumo de custos dos últimos N dias.
    Agrupado por agente e por modelo.
    """
    traces = load_traces(days=days, limit=10000)

    total_cost = 0.0
    total_tokens = 0
    by_agent: dict[str, dict] = {}
    by_model: dict[str, dict] = {}

    for t in traces:
        cost = t.get("cost_usd", 0.0)
        tokens = t.get("tokens_total", 0)
        agent = t.get("agent_name", "unknown")
        model = t.get("model", "unknown")

        total_cost += cost
        total_tokens += tokens

        if agent not in by_agent:
            by_agent[agent] = {"cost_usd": 0.0, "tokens": 0, "runs": 0}
        by_agent[agent]["cost_usd"] = round(by_agent[agent]["cost_usd"] + cost, 6)
        by_agent[agent]["tokens"] += tokens
        by_agent[agent]["runs"] += 1

        if model not in by_model:
            by_model[model] = {"cost_usd": 0.0, "tokens": 0, "calls": 0}
        by_model[model]["cost_usd"] = round(by_model[model]["cost_usd"] + cost, 6)
        by_model[model]["tokens"] += tokens
        by_model[model]["calls"] += 1

    # Ordenar por custo desc
    by_agent_sorted = dict(sorted(by_agent.items(), key=lambda x: x[1]["cost_usd"], reverse=True))
    by_model_sorted = dict(sorted(by_model.items(), key=lambda x: x[1]["cost_usd"], reverse=True))

    return {
        "days": days,
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "total_runs": len(traces),
        "by_agent": by_agent_sorted,
        "by_model": by_model_sorted,
    }
