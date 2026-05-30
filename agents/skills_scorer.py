"""
agents/skills_scorer.py — Scorer de skills com histórico de sucesso.

Complementa o CapabilityRegistry com dados da memória episódica.
Zero API — scoring puramente local.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_success_history(memory_path: str = "memory/episodica") -> dict[str, float]:
    """
    Extrai taxas de sucesso por agente da memória episódica.

    Lê ficheiros de log episódico e calcula success_rate por agente.
    Retorna dict {agent_name: success_rate (0.0-1.0)}.
    """
    import os
    import json

    history: dict[str, dict] = {}  # {agent: {success: int, total: int}}

    if not os.path.isdir(memory_path):
        return {}

    for fname in os.listdir(memory_path):
        if not fname.endswith(".json") and not fname.endswith(".jsonl"):
            continue

        fpath = os.path.join(memory_path, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Tentar parse como JSONL (linha por linha)
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    _process_entry(entry, history)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.debug(f"[SkillsScorer] Erro ao ler {fname}: {e}")

    # Calcular success rates
    rates = {}
    for agent, stats in history.items():
        total = stats.get("total", 0)
        if total > 0:
            rates[agent] = stats.get("success", 0) / total
        else:
            rates[agent] = 0.5  # neutral default

    if rates:
        logger.debug(f"[SkillsScorer] Hist?rico extra?do: {rates}")

    return rates


def _process_entry(entry: dict, history: dict):
    """Processa uma entrada do log episódico."""
    agent = entry.get("agent") or entry.get("agent_name")
    status = entry.get("status") or entry.get("result")

    if not agent:
        return

    if agent not in history:
        history[agent] = {"success": 0, "total": 0}

    history[agent]["total"] += 1

    if status in ("success", "completed", "done", "ok", True, "true"):
        history[agent]["success"] += 1


def score_task_complexity(task: str) -> float:
    """
    Estima complexidade de uma tarefa (0.0 = simples, 1.0 = muito complexa).

    Usado no Batch 6 para routing local vs DeepSeek.
    Sem API — heurísticas locais.
    """
    score = 0.0
    task_lower = task.lower()

    # Indicadores de complexidade
    complexity_signals = [
        # Alta complexidade
        (["arquitetura", "refatorar", "redesenhar", "sistema completo"], 0.3),
        (["integrar", "migrar", "converter", "transformar"], 0.2),
        (["otimizar performance", "profiling", "bottleneck"], 0.2),
        # Média complexidade
        (["implementar", "criar modulo", "nova feature"], 0.15),
        (["corrigir bug complexo", "debug", "traceback"], 0.15),
        # Baixa complexidade
        (["adicionar comentario", "renomear", "mover ficheiro"], 0.05),
        (["documentar", "readme", "atualizar"], 0.1),
    ]

    for signals, weight in complexity_signals:
        if any(s in task_lower for s in signals):
            score += weight

    # Comprimento como proxy de complexidade
    word_count = len(task.split())
    if word_count > 50:
        score += 0.2
    elif word_count > 20:
        score += 0.1

    # Múltiplos verbos = tarefa composta
    verbs = re.findall(r'\b(implementar|criar|corrigir|testar|documentar|refatorar|otimizar)\b', task_lower)
    if len(verbs) > 2:
        score += 0.2

    return min(score, 1.0)


def recommend_agent_with_reasoning(
    task: str,
    available_agents: Optional[list[str]] = None,
    memory_path: str = "memory/episodica"
) -> tuple[str, dict]:
    """
    Recomenda agente com explicação do raciocínio.

    Returns:
        (agent_name, reasoning_dict)
    """
    from agents.capability_registry import get_registry

    registry = get_registry()

    # Obter histórico de sucesso
    success_history = extract_success_history(memory_path)

    # Calcular scores
    scores = registry.score_all(task, success_history)

    # Filtrar por disponíveis
    if available_agents:
        scores = {k: v for k, v in scores.items() if k in available_agents}

    if not scores:
        return "supervisor", {"reason": "Nenhum agente disponível"}

    # Ordenar por score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_agent, best_score = ranked[0]

    # Fallback se score insuficiente
    if best_score <= 0:
        best_agent = "supervisor"

    reasoning = {
        "chosen": best_agent,
        "score": best_score,
        "top3": ranked[:3],
        "complexity": score_task_complexity(task),
        "history_used": bool(success_history),
    }

    return best_agent, reasoning
