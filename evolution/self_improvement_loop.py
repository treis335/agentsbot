"""
evolution/self_improvement_loop.py — Loop de auto-melhoria do sistema.

Ciclo completo (corre a cada N ciclos normais do autonomous_loop):

  1. LogAnalyzer      — analisa logs/episódios, encontra padrões (local, 0 API)
  2. ImprovementProposer — propõe melhorias concretas (1 chamada DeepSeek/ciclo)
  3. PatchGenerator   — gera código para as propostas (local ou LLM)
  4. PatchValidator   — valida sintaxe + que não quebra testes (local)
  5. Aplicar patches  — str_replace nos ficheiros reais
  6. Git commit       — persiste as mudanças com mensagem descritiva
  7. Notificar        — manda resumo via Telegram + guarda em changelog

Configuração (via .env ou Config):
  SELF_IMPROVE_EVERY_N_CYCLES = 10   (corre a cada 10 ciclos autónomos)
  SELF_IMPROVE_MAX_PATCHES     = 3   (máx patches por ciclo)
  SELF_IMPROVE_ENABLED         = true

Uso directo:
    loop = SelfImprovementLoop()
    result = await loop.run_cycle()
    print(result.summary)
"""

import asyncio
import json
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)

_CHANGELOG = Path("evolution") / "changelog_auto.md"
_CYCLE_COUNTER = Path("memory") / "self_improve_cycle.json"


@dataclass
class ImprovementResult:
    """Resultado de um ciclo de auto-melhoria."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    patterns_found: int = 0
    proposals_generated: int = 0
    patches_generated: int = 0
    patches_validated: int = 0
    patches_applied: int = 0
    committed: bool = False
    commit_hash: str = ""
    error: str = ""
    details: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.error:
            return f"[X] Self-improve falhou: {self.error}"
        if self.patches_applied == 0:
            return (
                f"[BUSCA] Self-improve: {self.patterns_found} padr?es encontrados, "
                f"sem patches aplic?veis neste ciclo."
            )
        return (
            f"[DNA] Auto-melhoria: {self.patches_applied} patch(es) aplicado(s) "
            f"de {self.proposals_generated} proposta(s). "
            f"{'Commit: ' + self.commit_hash[:8] if self.committed else 'Sem commit.'}"
        )

    @property
    def telegram_msg(self) -> str:
        if self.patches_applied == 0:
            return None  # Não notificar se não houve mudanças
        lines = [
            "[DNA] *Auto-melhoria aplicada!*",
            "",
            f"? Padr?es detectados: {self.patterns_found}",
            f"? Propostas geradas: {self.proposals_generated}",
            f"? Patches aplicados: {self.patches_applied}",
            "",
        ]
        for d in self.details[:5]:
            lines.append(f"  [OK] {d}")
        if self.committed:
            lines.append(f"\nCommit: `{self.commit_hash[:8]}`")
        return "\n".join(lines)


class SelfImprovementLoop:
    """
    Orquestrador do ciclo completo de auto-melhoria.

    Usa os módulos existentes:
      - LogAnalyzer (log_analyzer.py)
      - ImprovementProposer (improvement_proposer.py)
      - PatchGenerator (patch_generator.py)
      - PatchValidator (patch_validator.py)
    """

    def __init__(self, telegram_bot=None):
        self.telegram_bot = telegram_bot
        self.enabled = getattr(Config, "SELF_IMPROVE_ENABLED", True)
        self.every_n = getattr(Config, "SELF_IMPROVE_EVERY_N_CYCLES", 10)
        self.max_patches = getattr(Config, "SELF_IMPROVE_MAX_PATCHES", 3)
        self._cycle_count = self._load_cycle_count()

    # -- Controlo de ciclos -----------------------------------------------------

    def _load_cycle_count(self) -> int:
        try:
            if _CYCLE_COUNTER.exists():
                return json.loads(_CYCLE_COUNTER.read_text())["count"]
        except Exception:
            pass
        return 0

    def _save_cycle_count(self) -> None:
        _CYCLE_COUNTER.parent.mkdir(parents=True, exist_ok=True)
        _CYCLE_COUNTER.write_text(json.dumps({"count": self._cycle_count}))

    def should_run(self) -> bool:
        """True se é altura de correr um ciclo de auto-melhoria."""
        if not self.enabled:
            return False
        self._cycle_count += 1
        self._save_cycle_count()
        return self._cycle_count % self.every_n == 0

    # -- Ciclo principal --------------------------------------------------------

    async def run_cycle(self) -> ImprovementResult:
        """
        Executa um ciclo completo de auto-melhoria.
        Retorna ImprovementResult com o que foi feito.
        """
        result = ImprovementResult()
        logger.info("[SelfImprove] -- In?cio do ciclo de auto-melhoria --")

        try:
            # 1. Análise de logs (local, sem API)
            report = await self._analyze_logs(result)
            if not report:
                return result

            # 2. Propor melhorias (1 chamada API por ciclo)
            proposals = await self._propose_improvements(report, result)
            if not proposals:
                return result

            # 3. Gerar patches
            patches = await self._generate_patches(proposals, result)
            if not patches:
                return result

            # 4. Validar patches
            valid_patches = await self._validate_patches(patches, result)
            if not valid_patches:
                return result

            # 5. Aplicar patches
            applied = await self._apply_patches(valid_patches, result)

            # 6. Commit se houve mudanças
            if applied > 0:
                await self._commit_changes(result)

                # 7. Guardar no changelog
                self._write_changelog(result)

                # 8. Notificar via Telegram
                await self._notify(result)

        except Exception as e:
            result.error = str(e)
            logger.error(f"[SelfImprove] Erro no ciclo: {e}\n{traceback.format_exc()}")

        logger.info(f"[SelfImprove] {result.summary}")
        return result

    # -- Passos individuais -----------------------------------------------------

    async def _analyze_logs(self, result: ImprovementResult) -> Optional[dict]:
        """Passo 1: análise local de logs."""
        try:
            from evolution.log_analyzer import LogAnalyzer
            analyzer = LogAnalyzer()
            report = analyzer.analyze()
            patterns = len(report.get("top_errors", [])) + len(report.get("failing_agents", []))
            result.patterns_found = patterns
            logger.info(f"[SelfImprove] An?lise: {patterns} padr?es encontrados")
            return report
        except Exception as e:
            logger.warning(f"[SelfImprove] An?lise falhou: {e}")
            # Fallback: relatório mínimo baseado em ficheiros simples
            return self._minimal_report()

    def _minimal_report(self) -> dict:
        """Relatório mínimo quando LogAnalyzer falha — lê backlog directamente."""
        report = {"top_errors": [], "failing_agents": [], "suggestions": []}
        try:
            bf = Config.MEMORY_DIR / "backlog.json"
            if bf.exists():
                tasks = json.loads(bf.read_text(encoding="utf-8"))
                if not isinstance(tasks, list):
                    tasks = tasks.get("tasks", [])
                failed = [t for t in tasks if "fail" in t.get("status", "").lower()]
                for t in failed[:5]:
                    err = t.get("last_error", t.get("result", ""))[:100]
                    if err:
                        report["top_errors"].append({"error": err, "count": 1})
        except Exception:
            pass
        return report

    async def _propose_improvements(self, report: dict, result: ImprovementResult) -> list[dict]:
        """Passo 2: propor melhorias (1 chamada API)."""
        try:
            from evolution.improvement_proposer import ImprovementProposer
            proposer = ImprovementProposer()
            proposals = proposer.propose(report, max_proposals=self.max_patches)
            result.proposals_generated = len(proposals)
            logger.info(f"[SelfImprove] {len(proposals)} proposta(s) gerada(s)")
            return proposals
        except Exception as e:
            logger.warning(f"[SelfImprove] Propostas falharam: {e}")
            return []

    async def _generate_patches(self, proposals: list[dict], result: ImprovementResult) -> list[dict]:
        """Passo 3: gerar código para cada proposta."""
        try:
            from evolution.patch_generator import PatchGenerator
            generator = PatchGenerator()
            patches = []
            for proposal in proposals[:self.max_patches]:
                patch = generator.generate(proposal, use_llm=True)
                if patch:
                    patches.append(patch)
            result.patches_generated = len(patches)
            logger.info(f"[SelfImprove] {len(patches)} patch(es) gerado(s)")
            return patches
        except Exception as e:
            logger.warning(f"[SelfImprove] Gera??o de patches falhou: {e}")
            return []

    async def _validate_patches(self, patches: list[dict], result: ImprovementResult) -> list[dict]:
        """Passo 4: validar patches — sintaxe local + Conselho Multi-Agente."""
        from evolution.patch_validator import PatchValidator
        from evolution.council import get_council

        validator = PatchValidator()
        council = get_council()
        approved = []

        for patch in patches:
            desc = patch.get("description", "?")[:60]

            # 4a: validacao local (sintaxe, search_str existe)
            local_result = validator.validate(patch)
            if not local_result.get("valid", False):
                errors = local_result.get("errors", [])
                logger.warning(f"[SelfImprove] Sintaxe invalida: {'; '.join(str(e) for e in errors[:2])}")
                continue

            # 4b: Conselho Multi-Agente (4 agentes revisam)
            try:
                decision = council.review(patch)
                if decision.approved:
                    approved.append(patch)
                    logger.info(f"[Council] Aprovado ({decision.approve_count}/4): {desc}")
                else:
                    veto = " [VETO]" if decision.veto else ""
                    logger.warning(f"[Council] Rejeitado{veto}: {desc} — {decision.final_reasoning[:80]}")
            except Exception as e:
                # Council falhou — usar validacao local como fallback
                logger.warning(f"[Council] Fallback para validacao local: {e}")
                approved.append(patch)

        result.patches_validated = len(approved)
        logger.info(f"[SelfImprove] {len(approved)}/{len(patches)} patches aprovados")
        return approved

    async def _apply_patches(self, patches: list[dict], result: ImprovementResult) -> int:
        """Passo 5: aplicar patches nos ficheiros reais."""
        applied = 0
        repo_root = Config.REPO_LOCAL_PATH

        for patch in patches:
            try:
                target = repo_root / patch["target_file"]
                if not target.exists():
                    logger.warning(f"[SelfImprove] Ficheiro n?o encontrado: {patch['target_file']}")
                    continue

                content = target.read_text(encoding="utf-8")
                patch_type = patch.get("patch_type", "replace")

                if patch_type == "replace":
                    search = patch.get("search_str", "")
                    if not search or search not in content:
                        logger.warning(f"[SelfImprove] search_str n?o encontrado em {patch['target_file']}")
                        continue
                    new_content = content.replace(search, patch["replacement"], 1)
                elif patch_type == "append":
                    new_content = content + "\n" + patch["replacement"]
                elif patch_type == "insert_before":
                    search = patch.get("search_str", "")
                    if not search or search not in content:
                        continue
                    new_content = content.replace(search, patch["replacement"] + "\n" + search, 1)
                else:
                    continue

                target.write_text(new_content, encoding="utf-8")
                applied += 1
                desc = patch.get("description", patch["target_file"])[:70]
                result.details.append(desc)
                logger.info(f"[SelfImprove] [OK] Aplicado: {desc}")

            except Exception as e:
                logger.error(f"[SelfImprove] Erro ao aplicar patch: {e}")

        result.patches_applied = applied
        return applied

    async def _commit_changes(self, result: ImprovementResult) -> None:
        """Passo 6: commit git com mensagem descritiva."""
        try:
            import subprocess
            repo = str(Config.REPO_LOCAL_PATH)

            msg_lines = [
                f"self-improve: {result.patches_applied} melhoria(s) autom?tica(s)",
                "",
            ] + [f"- {d}" for d in result.details]

            subprocess.run(["git", "add", "-A"], cwd=repo, check=True,
                          capture_output=True, timeout=30)
            proc = subprocess.run(
                ["git", "commit", "-m", "\n".join(msg_lines)],
                cwd=repo, capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                # Obter hash do commit
                hash_proc = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo, capture_output=True, text=True, timeout=10
                )
                result.commit_hash = hash_proc.stdout.strip()
                result.committed = True
                logger.info(f"[SelfImprove] Commit: {result.commit_hash[:8]}")

                # Push
                subprocess.run(["git", "push", "origin", "main"],
                               cwd=repo, capture_output=True, timeout=60)
        except Exception as e:
            logger.warning(f"[SelfImprove] Commit falhou: {e}")

    def _write_changelog(self, result: ImprovementResult) -> None:
        """Passo 7: escrever no changelog automático."""
        try:
            _CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
            existing = _CHANGELOG.read_text(encoding="utf-8") if _CHANGELOG.exists() else ""

            entry = (
                f"\n## {result.timestamp[:16].replace('T', ' ')} "
                f"? {result.patches_applied} patch(es)\n\n"
            )
            for d in result.details:
                entry += f"- {d}\n"
            if result.committed:
                entry += f"\nCommit: `{result.commit_hash[:8]}`\n"

            _CHANGELOG.write_text(entry + existing, encoding="utf-8")
        except Exception as e:
            logger.warning(f"[SelfImprove] Changelog falhou: {e}")

    async def _notify(self, result: ImprovementResult) -> None:
        """Passo 8: notificar via Notifier singleton."""
        if result.patches_applied == 0:
            return
        try:
            from bot.notifier import get_notifier
            notifier = get_notifier()
            await notifier.self_improvement(
                patches=result.patches_applied,
                details=result.details,
                commit=result.commit_hash,
            )
        except Exception as e:
            logger.warning(f"[SelfImprove] Notifica??o falhou: {e}")
