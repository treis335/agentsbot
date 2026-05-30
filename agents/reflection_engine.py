"""
agents/reflection_engine.py — Sistema de Reflexão Pós-Tarefa.

Após cada execução, o agente analisa o que aconteceu e produz:
  1. O que correu bem (para reutilizar)
  2. O que correu mal (para evitar)
  3. Estratégia ajustada para próxima vez
  4. Se deve criar uma nova skill (quando padrão se repete 3x)

A reflexão é feita por heurísticas locais (zero API) para casos simples,
e com 1 chamada DeepSeek para casos complexos ou novos padrões.

As reflexões ficam em memory/reflections.json e são injectadas
no contexto antes das próximas tarefas similares.

Uso:
    engine = ReflectionEngine()
    reflection = engine.reflect(task, result, agent, success)
    # → Reflexão gravada, lição extraída, skill gerada se padrão repetido
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_REFLECTIONS_FILE = Path("memory") / "reflections.json"
_MAX_REFLECTIONS = 500


@dataclass
class Reflection:
    task_id: str
    task_desc: str
    agent: str
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    what_worked: str = ""
    what_failed: str = ""
    adjusted_strategy: str = ""
    new_skill_triggered: bool = False
    new_skill_name: str = ""
    raw_result: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt_context(self) -> str:
        """Formata para injectar num prompt."""
        icon = "✅" if self.success else "❌"
        lines = [f"{icon} Reflexão de tarefa similar ({self.timestamp[:10]}):"]
        if self.what_worked:
            lines.append(f"  • Funcionou: {self.what_worked}")
        if self.what_failed:
            lines.append(f"  • Falhou: {self.what_failed}")
        if self.adjusted_strategy:
            lines.append(f"  • Estratégia: {self.adjusted_strategy}")
        return "\n".join(lines)


class ReflectionEngine:
    """
    Motor de reflexão pós-tarefa.
    Analisa resultados e ajusta comportamento futuro sem chamadas API desnecessárias.
    """

    # Padrões de erro → estratégia corrigida (local, zero API)
    ERROR_PATTERNS = {
        r"cannot schedule new futures after shutdown": (
            "Erro de event loop asyncio",
            "Usar loop = asyncio.new_event_loop() em vez de asyncio.run() em threads"
        ),
        r"modulenotfounderror|no module named": (
            "Módulo Python não instalado",
            "Verificar imports e correr pip install antes de usar o módulo"
        ),
        r"filenotfounderror|no such file": (
            "Ficheiro ou directório não existe",
            "Verificar se o path existe com Path.exists() antes de ler/escrever"
        ),
        r"permissionerror|permission denied": (
            "Sem permissão de escrita",
            "Verificar permissões com os.access() ou usar directório temporário"
        ),
        r"unicodedecodeerror|unicodeencodeerror": (
            "Erro de encoding",
            "Usar encoding='utf-8', errors='replace' em todas as operações de ficheiro"
        ),
        r"returncode: [1-9]|exit code [1-9]": (
            "Comando shell falhou",
            "Verificar sintaxe do comando e se as dependências estão instaladas"
        ),
        r"timeout|timed out": (
            "Operação demasiado lenta",
            "Dividir em passos menores ou aumentar timeout"
        ),
        r"gitcommand\|git.*error\|failed to push": (
            "Erro Git",
            "Fazer git pull --rebase antes de push; verificar credenciais"
        ),
        r"peço desculpa|houve um erro técnico|não consigo": (
            "Agente capitulou sem tentar",
            "Usar ferramentas directamente em vez de explicar o problema"
        ),
        r"cannot write|write.*failed|erro ao escrever": (
            "Falha ao escrever ficheiro",
            "Usar write_file tool com retry; verificar se directório pai existe"
        ),
    }

    def __init__(self):
        self._reflections: list[dict] = self._load()
        self._pattern_counts: dict[str, int] = self._count_patterns()

    # ── Persistência ───────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        try:
            if _REFLECTIONS_FILE.exists():
                return json.loads(_REFLECTIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save(self) -> None:
        _REFLECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = self._reflections[-_MAX_REFLECTIONS:]
        _REFLECTIONS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _count_patterns(self) -> dict[str, int]:
        """Conta quantas vezes cada estratégia foi usada (para detectar skills)."""
        counts: dict[str, int] = {}
        for r in self._reflections:
            strat = r.get("adjusted_strategy", "")
            if strat:
                counts[strat] = counts.get(strat, 0) + 1
        return counts

    # ── Reflexão principal ─────────────────────────────────────────────────────

    def reflect(
        self,
        task_id: str,
        task_desc: str,
        agent: str,
        success: bool,
        result: str,
    ) -> Reflection:
        """
        Analisa o resultado de uma tarefa e produz reflexão.
        Usa heurísticas locais para casos comuns, zero API.
        """
        r = Reflection(
            task_id=task_id,
            task_desc=task_desc[:200],
            agent=agent,
            success=success,
            raw_result=result[:300],
        )

        if success:
            r.what_worked = self._extract_what_worked(task_desc, result)
            r.adjusted_strategy = f"Manter abordagem do {agent} para tarefas similares"
        else:
            r.what_failed, r.adjusted_strategy = self._analyze_failure(result)

        # Detectar se deve criar skill nova (padrão repetido 3x)
        if r.adjusted_strategy:
            count = self._pattern_counts.get(r.adjusted_strategy, 0) + 1
            self._pattern_counts[r.adjusted_strategy] = count
            if count >= 3 and not success:
                r.new_skill_triggered = True
                r.new_skill_name = self._generate_skill_name(r.adjusted_strategy)
                logger.info(f"[Reflection] Skill nova triggered: {r.new_skill_name}")
                self._register_skill(r.new_skill_name, r.adjusted_strategy, agent)

        self._reflections.append(r.to_dict())
        self._save()

        logger.debug(
            f"[Reflection] {task_id[:20]} "
            f"{'✅' if success else '❌'} "
            f"→ {r.adjusted_strategy[:60]}"
        )
        return r

    # ── Análise local ──────────────────────────────────────────────────────────

    def _extract_what_worked(self, task: str, result: str) -> str:
        """Extrai o que correu bem por keywords no resultado."""
        result_lower = result.lower()
        if any(w in result_lower for w in ["commit", "push", "git"]):
            return "Git operations executadas com sucesso"
        if any(w in result_lower for w in ["write_file", "ficheiro criado", "saved"]):
            return "Escrita de ficheiro funcionou"
        if any(w in result_lower for w in ["✅", "success", "ok", "concluí"]):
            return "Tarefa completada com ferramentas disponíveis"
        if "python" in task.lower():
            return "Código Python executado sem erros"
        return "Abordagem directa com ferramentas funcionou"

    def _analyze_failure(self, result: str) -> tuple[str, str]:
        """
        Analisa falha por padrões conhecidos.
        Retorna (o_que_falhou, estrategia_ajustada).
        """
        result_lower = result.lower()
        for pattern, (what_failed, strategy) in self.ERROR_PATTERNS.items():
            if re.search(pattern, result_lower):
                return what_failed, strategy
        # Genérico
        return "Resultado inesperado ou incompleto", "Dividir tarefa em passos menores e verificar cada um"

    def _generate_skill_name(self, strategy: str) -> str:
        """Gera nome de skill a partir da estratégia."""
        words = strategy.lower().split()[:4]
        name = "_".join(w for w in words if len(w) > 3)
        return f"auto_skill_{name}"[:40]

    def _register_skill(self, name: str, strategy: str, agent: str) -> None:
        """Regista nova skill no SkillsManager."""
        try:
            from agents.skills_manager import SkillsManager
            sm = SkillsManager()
            sm.learn_skill(
                name=name,
                category="auto_generated",
                description=f"Skill automática: {strategy}. Gerada por {agent}.",
            )
            logger.info(f"[Reflection] ✨ Nova skill registada: {name}")
        except Exception as e:
            logger.warning(f"[Reflection] Falha ao registar skill: {e}")

    # ── Contexto para prompts ──────────────────────────────────────────────────

    def get_relevant_reflections(self, task_desc: str, limit: int = 3) -> list[Reflection]:
        """Retorna reflexões relevantes para uma tarefa (por similaridade de palavras)."""
        task_words = set(task_desc.lower().split())
        scored = []
        for r_dict in reversed(self._reflections):
            r_words = set(r_dict.get("task_desc", "").lower().split())
            score = len(task_words & r_words) / max(len(task_words | r_words), 1)
            if score > 0.15:
                scored.append((score, r_dict))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            Reflection(**{k: v for k, v in r.items() if k != "new_skill_triggered"
                         and k in Reflection.__dataclass_fields__},
                       new_skill_triggered=r.get("new_skill_triggered", False))
            for _, r in scored[:limit]
        ]

    def get_prompt_context(self, task_desc: str) -> str:
        """Retorna contexto de reflexões para injectar num prompt."""
        refs = self.get_relevant_reflections(task_desc)
        if not refs:
            return ""
        lines = ["\n## REFLEXÕES DE TAREFAS SIMILARES"]
        for r in refs:
            lines.append(r.to_prompt_context())
        lines.append("")
        return "\n".join(lines)

    def stats(self) -> dict:
        total = len(self._reflections)
        success = sum(1 for r in self._reflections if r.get("success"))
        skills_generated = sum(1 for r in self._reflections if r.get("new_skill_triggered"))
        return {
            "total_reflections": total,
            "successful": success,
            "failed": total - success,
            "skills_auto_generated": skills_generated,
            "top_failures": self._top_failures(5),
        }

    def _top_failures(self, n: int) -> list[dict]:
        counts: dict[str, int] = {}
        for r in self._reflections:
            if not r.get("success") and r.get("what_failed"):
                wf = r["what_failed"]
                counts[wf] = counts.get(wf, 0) + 1
        return sorted(
            [{"issue": k, "count": v} for k, v in counts.items()],
            key=lambda x: -x["count"]
        )[:n]


# Singleton
_engine: Optional[ReflectionEngine] = None

def get_reflection_engine() -> ReflectionEngine:
    global _engine
    if _engine is None:
        _engine = ReflectionEngine()
    return _engine
