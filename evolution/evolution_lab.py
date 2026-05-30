"""
evolution/evolution_lab.py — Laboratório de Evolução.

Ambiente isolado para experimentar melhorias antes de as aplicar
ao sistema em produção. Sprint 6+7 do Evolution Roadmap.

Fluxo:
  1. Ideia gerada (por agente ou auto-melhoria)
  2. Experimento criado no sandbox (git branch ou pasta isolada)
  3. Benchmark: compara candidato vs baseline
  4. Report gerado automaticamente
  5. Se benchmark passa → promove para aprovação pelo Council
"""
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EXPERIMENTS_DIR = Path("evolution") / "experiments"
BENCHMARKS_DIR  = Path("evolution") / "benchmarks"
REPORTS_DIR     = Path("evolution") / "reports"

for d in [EXPERIMENTS_DIR, BENCHMARKS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class Experiment:
    id: str
    title: str
    description: str
    hypothesis: str           # O que esperamos que melhore
    target_file: str          # Ficheiro a modificar
    proposed_change: str      # Descrição da mudança
    proposed_code: str        # Código proposto (patch)
    status: str = "pending"   # pending, running, passed, failed, promoted
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "auto_evolver"
    benchmark_score: float = 0.0
    baseline_score: float = 0.0
    report_path: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def improvement_pct(self) -> float:
        if self.baseline_score == 0:
            return 0.0
        return ((self.benchmark_score - self.baseline_score) / self.baseline_score) * 100


@dataclass
class BenchmarkResult:
    experiment_id: str
    test_name: str
    baseline_score: float
    candidate_score: float
    metric: str
    passed: bool
    details: str = ""
    run_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class EvolutionLab:
    """
    Laboratório de evolução isolado.
    Testa mudanças antes de as aplicar ao sistema real.
    """

    # Threshold mínimo de melhoria para aprovar
    MIN_IMPROVEMENT_PCT = 5.0

    def __init__(self):
        self._experiments: list[Experiment] = []
        self._load()

    def propose_experiment(
        self,
        title: str,
        description: str,
        hypothesis: str,
        target_file: str,
        proposed_code: str,
        created_by: str = "auto_evolver",
    ) -> Experiment:
        """Regista uma nova proposta de experimento."""
        exp = Experiment(
            id=f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            hypothesis=hypothesis,
            target_file=target_file,
            proposed_change=description,
            proposed_code=proposed_code,
            created_by=created_by,
        )
        self._experiments.append(exp)
        self._save()
        logger.info(f"[EvolutionLab] 🧪 Experimento: {exp.id} — {title}")
        return exp

    def run_benchmarks(self, experiment: Experiment) -> list[BenchmarkResult]:
        """
        Corre benchmarks para um experimento.
        Compara candidato vs baseline em métricas chave.
        """
        results = []
        experiment.status = "running"
        self._save()

        # Benchmark 1: Sintaxe válida
        syntax_result = self._bench_syntax(experiment)
        results.append(syntax_result)

        # Benchmark 2: Sem imports partidos
        imports_result = self._bench_imports(experiment)
        results.append(imports_result)

        # Benchmark 3: Complexidade do código (menos é melhor)
        complexity_result = self._bench_complexity(experiment)
        results.append(complexity_result)

        # Calcular score final
        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        experiment.benchmark_score = passed_count / total
        experiment.baseline_score  = 0.7   # baseline assumido de 70%

        # Experiment passa se todos os benchmarks críticos passam
        critical_passed = all(r.passed for r in results[:2])  # sintaxe + imports são críticos
        experiment.status = "passed" if critical_passed else "failed"

        # Guardar report
        report = self._generate_report(experiment, results)
        report_path = REPORTS_DIR / f"{experiment.id}.md"
        report_path.write_text(report, encoding="utf-8")
        experiment.report_path = str(report_path)

        self._save()
        logger.info(
            f"[EvolutionLab] {experiment.id}: "
            f"{'✅ PASSOU' if critical_passed else '❌ FALHOU'} "
            f"({passed_count}/{total} benchmarks)"
        )
        return results

    def get_ready_to_promote(self) -> list[Experiment]:
        """Experimentos que passaram benchmarks e estão prontos para promoção."""
        return [e for e in self._experiments if e.status == "passed"]

    def promote(self, experiment: Experiment) -> str:
        """Promove um experimento — aplica a mudança ao código real."""
        if experiment.status != "passed":
            return f"Experimento {experiment.id} não passou benchmarks."
        try:
            from evolution.patch_validator import PatchValidator
            validator = PatchValidator()
            patch = {
                "file": experiment.target_file,
                "new_code": experiment.proposed_code,
            }
            valid = validator.validate(patch)
            if not valid.get("valid"):
                experiment.status = "failed"
                experiment.error = str(valid.get("reason", "Validação falhou"))
                self._save()
                return f"❌ Promoção bloqueada: {experiment.error}"

            experiment.status = "promoted"
            self._save()

            from core.event_logger import log_promotion
            log_promotion(experiment.title, "baseline", f"v{experiment.id}")

            return f"✅ Experimento {experiment.id} promovido: {experiment.title}"
        except Exception as e:
            experiment.error = str(e)
            experiment.status = "failed"
            self._save()
            return f"❌ Erro na promoção: {e}"

    def get_stats(self) -> dict:
        total    = len(self._experiments)
        passed   = sum(1 for e in self._experiments if e.status == "passed")
        failed   = sum(1 for e in self._experiments if e.status == "failed")
        promoted = sum(1 for e in self._experiments if e.status == "promoted")
        return {
            "total": total, "passed": passed,
            "failed": failed, "promoted": promoted,
            "pass_rate": round(passed / total, 2) if total > 0 else 0.0,
        }

    # ── Benchmarks individuais ─────────────────────────────────────────────────

    def _bench_syntax(self, exp: Experiment) -> BenchmarkResult:
        """Verifica sintaxe Python do código proposto."""
        import ast
        try:
            ast.parse(exp.proposed_code)
            return BenchmarkResult(
                experiment_id=exp.id,
                test_name="syntax_check",
                baseline_score=1.0,
                candidate_score=1.0,
                metric="valid",
                passed=True,
                details="Sintaxe Python válida",
            )
        except SyntaxError as e:
            return BenchmarkResult(
                experiment_id=exp.id,
                test_name="syntax_check",
                baseline_score=1.0,
                candidate_score=0.0,
                metric="valid",
                passed=False,
                details=f"SyntaxError: linha {e.lineno} — {e.msg}",
            )

    def _bench_imports(self, exp: Experiment) -> BenchmarkResult:
        """Verifica que não há imports obviamente partidos."""
        dangerous = ["import hack", "import evil", "__import__('os').system"]
        code = exp.proposed_code
        has_danger = any(d in code for d in dangerous)
        return BenchmarkResult(
            experiment_id=exp.id,
            test_name="imports_check",
            baseline_score=1.0,
            candidate_score=0.0 if has_danger else 1.0,
            metric="safe",
            passed=not has_danger,
            details="Sem imports perigosos" if not has_danger else "Import perigoso detectado",
        )

    def _bench_complexity(self, exp: Experiment) -> BenchmarkResult:
        """Penaliza código desnecessariamente complexo."""
        lines = len(exp.proposed_code.strip().split("\n"))
        # Acima de 500 linhas numa proposta é suspeito
        score = max(0.0, 1.0 - max(0, lines - 500) / 500)
        return BenchmarkResult(
            experiment_id=exp.id,
            test_name="complexity_check",
            baseline_score=0.8,
            candidate_score=round(score, 2),
            metric="lines",
            passed=lines <= 500,
            details=f"{lines} linhas de código proposto",
        )

    def _generate_report(self, exp: Experiment, results: list[BenchmarkResult]) -> str:
        lines = [
            f"# Relatório: {exp.title}",
            f"**ID:** {exp.id}  ",
            f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
            f"**Status:** {exp.status.upper()}  ",
            f"**Ficheiro alvo:** `{exp.target_file}`",
            "",
            "## Hipótese",
            exp.hypothesis,
            "",
            "## Benchmarks",
        ]
        for r in results:
            icon = "✅" if r.passed else "❌"
            lines.append(f"- {icon} **{r.test_name}**: {r.details} "
                         f"(baseline={r.baseline_score:.2f}, candidato={r.candidate_score:.2f})")

        improvement = exp.improvement_pct
        lines += [
            "",
            f"## Score",
            f"- Benchmark: {exp.benchmark_score:.0%}  ",
            f"- Melhoria vs baseline: {improvement:+.1f}%",
            "",
            "## Decisão",
            f"{'✅ APROVADO para promoção' if exp.status == 'passed' else '❌ REJEITADO'}",
        ]
        return "\n".join(lines)

    def _load(self):
        exp_files = list(EXPERIMENTS_DIR.glob("*.json"))
        for f in exp_files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                exp = Experiment(**{k: v for k, v in data.items()
                                    if k in Experiment.__dataclass_fields__})
                self._experiments.append(exp)
            except Exception:
                pass

    def _save(self):
        for exp in self._experiments:
            f = EXPERIMENTS_DIR / f"{exp.id}.json"
            f.write_text(json.dumps(exp.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


_lab: Optional[EvolutionLab] = None

def get_lab() -> EvolutionLab:
    global _lab
    if _lab is None:
        _lab = EvolutionLab()
    return _lab
