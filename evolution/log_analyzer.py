"""
evolution/log_analyzer.py — Analisa logs de falhas e identifica padrões.

100% local — sem LLM. Heurísticas e estatísticas sobre memória episódica.
Produz um relatório estruturado de bottlenecks e padrões recorrentes.
"""

import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """
    Analisa logs episódicos e de falhas para identificar padrões.

    Produz:
    - Top erros mais frequentes
    - Agentes com maior taxa de falha
    - Padrões de retry excessivo
    - Tarefas que sempre falham
    - Sugestões de melhoria (heurísticas locais)
    """

    def __init__(self):
        self.episodic_dir = Config.MEMORY_DIR / "episodica"
        self.failures_dir = Config.MEMORY_DIR / "failures"
        self.backlog_file = Config.MEMORY_DIR / "backlog.json"

    def _load_all_episodes(self) -> list[dict]:
        """Carrega todos os episódios de todos os agentes."""
        all_eps = []
        if not self.episodic_dir.exists():
            return []
        for f in self.episodic_dir.glob("*.json"):
            try:
                eps = json.loads(f.read_text(encoding="utf-8"))
                for ep in eps:
                    ep.setdefault("_agent_file", f.stem)
                all_eps.extend(eps)
            except Exception:
                pass
        return all_eps

    def _load_all_failures(self) -> list[dict]:
        """Carrega todas as falhas estruturadas."""
        all_fails = []
        if not self.failures_dir.exists():
            return []
        for f in self.failures_dir.glob("*.json"):
            try:
                fails = json.loads(f.read_text(encoding="utf-8"))
                all_fails.extend(fails)
            except Exception:
                pass
        return all_fails

    def _load_backlog(self) -> list[dict]:
        """Carrega backlog de tarefas."""
        if not self.backlog_file.exists():
            # Tentar path alternativo
            alt = Config.REPO_LOCAL_PATH / "memory" / "backlog.json"
            if alt.exists():
                try:
                    return json.loads(alt.read_text(encoding="utf-8"))
                except Exception:
                    pass
            return []
        try:
            return json.loads(self.backlog_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def analyze(self, days_back: int = 7) -> dict:
        """
        Executa análise completa.

        Args:
            days_back: Quantos dias de histórico analisar

        Returns:
            Relatório estruturado com padrões e sugestões
        """
        cutoff = datetime.now() - timedelta(days=days_back)
        episodes = self._load_all_episodes()
        failures = self._load_all_failures()
        backlog = self._load_backlog()

        # Filtrar por período
        recent_eps = self._filter_recent(episodes, cutoff)
        recent_fails = self._filter_recent(failures, cutoff)

        report = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days_back,
            "totals": self._calc_totals(recent_eps, recent_fails, backlog),
            "error_patterns": self._top_error_patterns(recent_eps, recent_fails),
            "agent_performance": self._agent_performance(recent_eps),
            "retry_hotspots": self._retry_hotspots(backlog),
            "recurring_failures": self._recurring_failures(recent_fails),
            "suggestions": [],  # Preenchido abaixo
        }

        report["suggestions"] = self._generate_suggestions(report)

        logger.info(
            f"[LogAnalyzer] An?lise conclu?da: "
            f"{report['totals']['total_episodes']} epis?dios, "
            f"{len(report['suggestions'])} sugest?es"
        )
        return report

    def _filter_recent(self, items: list, cutoff: datetime) -> list:
        result = []
        for item in items:
            ts_str = item.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts >= cutoff:
                    result.append(item)
            except Exception:
                result.append(item)  # Sem timestamp: incluir
        return result

    def _calc_totals(self, eps: list, fails: list, backlog: list) -> dict:
        total = len(eps)
        successes = sum(1 for e in eps if e.get("success", True))
        failures_count = total - successes
        return {
            "total_episodes": total,
            "successes": successes,
            "failures": failures_count,
            "failure_rate": round(failures_count / total, 3) if total else 0,
            "structured_failures": len(fails),
            "backlog_total": len(backlog),
            "backlog_pending": sum(1 for t in backlog if t.get("status") == "pending"),
            "backlog_failed": sum(1 for t in backlog if t.get("status") == "failed"),
        }

    def _top_error_patterns(self, eps: list, fails: list) -> list[dict]:
        """Top 5 padrões de erro mais frequentes."""
        error_counts: Counter = Counter()

        # De episódios
        for ep in eps:
            if not ep.get("success", True):
                result = ep.get("episode", {}).get("result", "")
                pattern = self._classify_error_text(result)
                if pattern:
                    error_counts[pattern] += 1

        # De falhas estruturadas
        for f in fails:
            et = f.get("error_type", "")
            if et:
                error_counts[et] += 1

        top = error_counts.most_common(5)
        return [{"pattern": p, "count": c} for p, c in top]

    def _classify_error_text(self, text: str) -> Optional[str]:
        """Classifica texto de erro numa categoria."""
        text = text.lower()
        patterns = [
            (r"permission denied|permissionerror", "permission_error"),
            (r"no such file|filenotfounderror", "file_not_found"),
            (r"syntaxerror|indentationerror", "syntax_error"),
            (r"importerror|modulenotfounderror", "import_error"),
            (r"timeout|timed out", "timeout"),
            (r"connection|refused|network", "connection_error"),
            (r"git.*rejected|push.*rejected", "git_rejected"),
            (r"traceback|exception", "generic_exception"),
        ]
        for pattern, category in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category
        return None

    def _agent_performance(self, eps: list) -> list[dict]:
        """Taxa de sucesso por agente."""
        agent_stats: dict[str, dict] = defaultdict(lambda: {"success": 0, "total": 0})
        for ep in eps:
            agent = ep.get("_agent_file", ep.get("agent", "unknown"))
            agent_stats[agent]["total"] += 1
            if ep.get("success", True):
                agent_stats[agent]["success"] += 1

        result = []
        for agent, stats in agent_stats.items():
            total = stats["total"]
            if total == 0:
                continue
            rate = round(stats["success"] / total, 3)
            result.append({
                "agent": agent,
                "success_rate": rate,
                "total": total,
                "failures": total - stats["success"],
            })

        return sorted(result, key=lambda x: x["success_rate"])

    def _retry_hotspots(self, backlog: list) -> list[dict]:
        """Tarefas com muitos retries — indica problemas recorrentes."""
        hotspots = []
        for task in backlog:
            retry = task.get("retry_count", 0)
            if retry >= 2:
                hotspots.append({
                    "title": task.get("title", "?")[:80],
                    "retry_count": retry,
                    "status": task.get("status", "?"),
                    "last_error": task.get("last_error", "")[:120],
                })
        return sorted(hotspots, key=lambda x: x["retry_count"], reverse=True)[:5]

    def _recurring_failures(self, fails: list) -> list[dict]:
        """Falhas do mesmo tipo que se repetem sem resolução."""
        unresolved_by_type: Counter = Counter()
        for f in fails:
            if not f.get("resolved", False):
                unresolved_by_type[f.get("error_type", "unknown")] += 1

        return [
            {"error_type": et, "unresolved_count": c}
            for et, c in unresolved_by_type.most_common(5)
            if c >= 2
        ]

    def _generate_suggestions(self, report: dict) -> list[dict]:
        """
        Gera sugestões baseadas nos padrões encontrados.
        Heurísticas locais — sem LLM.
        """
        suggestions = []
        totals = report["totals"]
        patterns = report["error_patterns"]
        agent_perf = report["agent_performance"]
        retry_spots = report["retry_hotspots"]

        # Alta taxa de falha global
        if totals["failure_rate"] > 0.3:
            suggestions.append({
                "type": "high_failure_rate",
                "priority": "high",
                "description": (
                    f"Taxa de falha de {totals['failure_rate']*100:.0f}% est? elevada. "
                    "Considerar aumentar timeout ou melhorar tratamento de erros."
                ),
                "action": "review_error_handling",
            })

        # Padrões de erro frequentes
        for p in patterns[:2]:
            if p["count"] >= 3:
                action_map = {
                    "permission_error": "Adicionar verificação de permissões antes de escrever ficheiros",
                    "file_not_found": "Criar directórios com mkdir -p antes de operações de ficheiro",
                    "syntax_error": "Adicionar validação de sintaxe (py_compile) antes de executar código",
                    "import_error": "Verificar requirements.txt e instalar dependências em falta",
                    "timeout": "Aumentar timeouts ou dividir tarefas longas em sub-tarefas",
                    "git_rejected": "Fazer git pull antes de push para evitar conflitos",
                }
                suggestion_text = action_map.get(
                    p["pattern"],
                    f"Padr?o '{p['pattern']}' aparece {p['count']}x ? investigar causa raiz"
                )
                suggestions.append({
                    "type": "recurring_error",
                    "priority": "medium",
                    "description": suggestion_text,
                    "action": f"fix_{p['pattern']}",
                    "error_count": p["count"],
                })

        # Agentes com baixa performance
        for agent in agent_perf:
            if agent["success_rate"] < 0.5 and agent["total"] >= 5:
                suggestions.append({
                    "type": "low_performance_agent",
                    "priority": "medium",
                    "description": (
                        f"Agente '{agent['agent']}' tem taxa de sucesso de "
                        f"{agent['success_rate']*100:.0f}% ({agent['failures']} falhas). "
                        "Rever soul ou tarefas atribuídas."
                    ),
                    "action": f"review_agent_{agent['agent']}",
                    "agent": agent["agent"],
                })

        # Retry hotspots
        for spot in retry_spots[:2]:
            suggestions.append({
                "type": "retry_hotspot",
                "priority": "low",
                "description": (
                    f"Tarefa '{spot['title']}' retentada {spot['retry_count']}x. "
                    f"?ltimo erro: {spot['last_error'][:80]}"
                ),
                "action": "investigate_task",
            })

        # Backlog com muitas tarefas falhadas
        if totals["backlog_failed"] >= 5:
            suggestions.append({
                "type": "backlog_debt",
                "priority": "low",
                "description": (
                    f"{totals['backlog_failed']} tarefas falharam no backlog. "
                    "Considerar limpeza ou re-priorização."
                ),
                "action": "clean_backlog",
            })

        return sorted(suggestions, key=lambda s: {"high": 0, "medium": 1, "low": 2}[s["priority"]])
