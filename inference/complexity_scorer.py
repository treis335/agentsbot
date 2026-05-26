"""
inference/complexity_scorer.py — Score local de complexidade de uma tarefa.

Zero chamadas API. Heurísticas baseadas em:
- Comprimento e estrutura da tarefa
- Keywords de alta/baixa complexidade
- Número de ficheiros envolvidos
- Histórico de sucesso (se disponível)

Score: 0.0 (trivial) a 1.0 (altamente complexo)
Threshold recomendado: < 0.4 → Ollama local; >= 0.4 → DeepSeek
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ComplexityResult:
    score: float           # 0.0 – 1.0
    label: str             # "low" | "medium" | "high"
    reason: str            # explicação legível
    use_local: bool        # True → Ollama; False → DeepSeek


# ─── KEYWORDS ──────────────────────────────────────────────────────────────────

# Tarefas simples → Ollama consegue
LOW_COMPLEXITY_KEYWORDS = {
    # leitura e análise simples
    "list", "show", "read", "get", "fetch", "check", "status",
    "listar", "mostrar", "ler", "verificar", "estado", "listar ficheiros",
    # formatação e texto
    "format", "rename", "comment", "docstring", "log",
    "formatar", "comentar", "renomear",
    # git simples
    "git status", "git log", "git diff", "git add", "commit message",
    # sintaxe e lint
    "syntax", "lint", "style", "pep8", "type hint",
    # documentação simples
    "readme", "changelog", "update docs", "atualizar docs",
    # debug simples
    "print", "debug", "trace", "typo", "indentation",
}

# Tarefas complexas → DeepSeek necessário
HIGH_COMPLEXITY_KEYWORDS = {
    # arquitectura
    "architect", "design pattern", "refactor", "redesign", "migrate",
    "arquitetura", "refactori", "migrar", "redesenhar",
    # segurança
    "security", "vulnerability", "exploit", "auth", "encrypt",
    "segurança", "vulnerabilidade", "autenticação",
    # algoritmos
    "algorithm", "optimization", "performance", "concurrency", "async",
    "algoritmo", "otimização", "concorrência",
    # multi-ficheiro
    "multiple files", "across files", "system-wide", "global change",
    "vários ficheiros", "mudança global",
    # lógica de negócio complexa
    "workflow", "pipeline", "orchestrat", "state machine",
    "integration", "api design", "database schema",
    # criatividade
    "create new", "build", "implement", "from scratch",
    "criar de raiz", "implementar do zero",
}


def score_task(
    task: str,
    context_size: int = 0,
    num_files: int = 0,
    past_failures: int = 0,
) -> ComplexityResult:
    """
    Calcula score de complexidade de uma tarefa.

    Args:
        task: texto da tarefa
        context_size: tamanho do contexto de conversação (chars)
        num_files: número de ficheiros envolvidos (se conhecido)
        past_failures: falhas anteriores nesta tarefa

    Returns:
        ComplexityResult com score, label, razão e recomendação
    """
    task_lower = task.lower()
    reasons = []
    score = 0.0

    # ── 1. Comprimento da tarefa ────────────────────────────────────────────────
    task_len = len(task)
    if task_len < 50:
        score += 0.0
        reasons.append(f"tarefa curta ({task_len} chars)")
    elif task_len < 150:
        score += 0.1
    elif task_len < 400:
        score += 0.2
        reasons.append(f"tarefa média ({task_len} chars)")
    else:
        score += 0.35
        reasons.append(f"tarefa longa ({task_len} chars)")

    # ── 2. Keywords de baixa complexidade (penaliza score) ─────────────────────
    low_hits = [kw for kw in LOW_COMPLEXITY_KEYWORDS if kw in task_lower]
    if low_hits:
        score -= 0.15
        reasons.append(f"keywords simples: {', '.join(low_hits[:3])}")

    # ── 3. Keywords de alta complexidade ───────────────────────────────────────
    high_hits = [kw for kw in HIGH_COMPLEXITY_KEYWORDS if kw in task_lower]
    if high_hits:
        score += 0.25 * min(len(high_hits), 2)  # máximo de +0.5
        reasons.append(f"keywords complexas: {', '.join(high_hits[:3])}")

    # ── 4. Número de ficheiros ──────────────────────────────────────────────────
    # Contar menções a caminhos de ficheiros no texto
    file_mentions = len(re.findall(r'\b\w+\.\w{2,4}\b', task))
    if file_mentions == 0 and num_files == 0:
        pass
    elif file_mentions <= 1 or num_files <= 1:
        score += 0.05
    elif file_mentions <= 3 or num_files <= 3:
        score += 0.15
        reasons.append(f"{max(file_mentions, num_files)} ficheiros envolvidos")
    else:
        score += 0.25
        reasons.append(f"muitos ficheiros ({max(file_mentions, num_files)})")

    # ── 5. Contexto de conversação ─────────────────────────────────────────────
    if context_size > 10000:
        score += 0.1
        reasons.append("contexto longo")

    # ── 6. Falhas anteriores ───────────────────────────────────────────────────
    if past_failures > 0:
        score += 0.15 * min(past_failures, 2)
        reasons.append(f"{past_failures} falha(s) anterior(es)")

    # ── 7. Indicadores de multi-passo ──────────────────────────────────────────
    step_indicators = ["1.", "2.", "3.", "primeiro", "depois", "then", "finally",
                       "passo", "step", "seguida", "after"]
    step_count = sum(1 for si in step_indicators if si in task_lower)
    if step_count >= 3:
        score += 0.15
        reasons.append(f"tarefa multi-passo ({step_count} indicadores)")

    # ── Normalizar score ───────────────────────────────────────────────────────
    score = max(0.0, min(1.0, score))

    # ── Label e recomendação ───────────────────────────────────────────────────
    from core.config import Config
    threshold = getattr(Config, "ROUTING_THRESHOLD", 0.4)

    if score < 0.25:
        label = "low"
    elif score < threshold:
        label = "medium"
    else:
        label = "high"

    use_local = score < threshold
    reason_str = "; ".join(reasons) if reasons else "heurísticas base"

    return ComplexityResult(
        score=round(score, 3),
        label=label,
        reason=reason_str,
        use_local=use_local,
    )


def quick_check(task: str) -> bool:
    """
    Verificação rápida: True se deve usar local (Ollama).
    Versão optimizada para hot path sem instanciar o dataclass.
    """
    return score_task(task).use_local
