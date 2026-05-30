"""
evolution/council.py — Conselho Multi-Agente para revisão de patches.

Antes de qualquer patch ser aplicado ao sistema, 4 agentes especialistas
analisam-no independentemente. A decisão final é por maioria.

Membros do Conselho:
  🏛️  Arquitecto   — impacto na coerência global e arquitectura
  💻  Programador  — qualidade do código, bugs, edge cases
  🧪  Testador     — riscos de regressão, cobertura de testes
  📋  Revisor      — agrega os votos e dá veredicto final

Cada membro responde com:
  {
    "vote": "approve" | "reject" | "abstain",
    "confidence": 0-10,
    "reasoning": "...",
    "concerns": ["..."]
  }

Regras:
  - Aprovado se >= 3 votos approve (maioria qualificada)
  - Rejeitado automaticamente se Arquitecto rejeitar com confidence >= 8
  - Dry-run disponível para simular sem aplicar

Custo API: 1 chamada DeepSeek por membro por patch (máx 4 por patch).
Para patches simples (só sintaxe/docs), usa validação local sem LLM.
"""

# ============================================================
# FIX: Forcar UTF-8 no stdout/stderr para evitar UnicodeEncodeError
# com emojis no Windows (CP1252)
# ============================================================
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)

_COUNCIL_LOG = Path("evolution") / "council_log.jsonl"


@dataclass
class MemberVote:
    member: str
    role: str
    vote: str           # "approve" | "reject" | "abstain"
    confidence: int     # 0-10
    reasoning: str
    concerns: list[str] = field(default_factory=list)

    @property
    def approves(self) -> bool:
        return self.vote == "approve"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CouncilDecision:
    patch_description: str
    patch_file: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    votes: list[MemberVote] = field(default_factory=list)
    approved: bool = False
    final_reasoning: str = ""
    veto: bool = False          # True se veto automático (arquitecto confidence >= 8)
    local_only: bool = False    # True se validado só por heurísticas

    @property
    def approve_count(self) -> int:
        return sum(1 for v in self.votes if v.approves)

    @property
    def reject_count(self) -> int:
        return sum(1 for v in self.votes if v.vote == "reject")

    def summary(self) -> str:
        if self.local_only:
            return f"{'✅' if self.approved else '❌'} Local [{self.patch_file}]: {self.final_reasoning}"
        votes_str = " | ".join(
            f"{'✅' if v.approves else '❌'} {v.member}({v.confidence})"
            for v in self.votes
        )
        result = "✅ APROVADO" if self.approved else "❌ REJEITADO"
        veto_note = " [VETO]" if self.veto else ""
        return f"{result}{veto_note} {votes_str} — {self.patch_file}"

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ── Prompts dos membros ────────────────────────────────────────────────────────

def _member_prompt(role: str, patch: dict, file_content: str) -> str:
    """Constrói o prompt para cada membro do conselho."""
    patch_desc = patch.get("description", "sem descrição")[:200]
    target = patch.get("target_file", "?")
    search = patch.get("search_str", "")[:300]
    replacement = patch.get("replacement", "")[:500]

    role_instructions = {
        "arquiteto": (
            "Analisa o impacto na arquitectura global. Verifica se o patch:\n"
            "- Respeita os princípios SOLID e a estrutura existente\n"
            "- Não cria dependências circulares\n"
            "- Não quebra interfaces públicas\n"
            "- É coerente com o resto do sistema"
        ),
        "programador": (
            "Analisa a qualidade do código. Verifica se o patch:\n"
            "- Não introduz bugs óbvios ou edge cases não tratados\n"
            "- Tem error handling adequado\n"
            "- Não tem código duplicado desnecessário\n"
            "- Usa as convenções do projeto"
        ),
        "testador": (
            "Analisa os riscos de regressão. Verifica se o patch:\n"
            "- Pode quebrar funcionalidade existente\n"
            "- Os testes existentes continuarão a passar\n"
            "- Há casos extremos não cobertos\n"
            "- Precisa de novos testes para ser seguro"
        ),
        "revisor": (
            "Agrega as preocupações e decide o veredicto final. Considera:\n"
            "- O benefício esperado vale o risco?\n"
            "- As preocupações dos outros membros são críticas ou menores?\n"
            "- O patch pode ser melhorado em vez de rejeitado?\n"
            "- É melhor aplicar agora ou adiar?"
        ),
    }

    return f"""És o {role.upper()} do Conselho de Revisão de Patches do sistema CORREOTO.

PATCH A ANALISAR:
Descrição: {patch_desc}
Ficheiro: {target}
Tipo: {patch.get('patch_type', 'replace')}

CÓDIGO A SUBSTITUIR:
```
{search}
```

CÓDIGO NOVO:
```
{replacement}
```

CONTEXTO DO FICHEIRO (primeiras 200 linhas):
```
{file_content[:2000]}
```

{role_instructions.get(role, '')}

Responde APENAS em JSON válido (sem markdown, sem texto extra):
{{
  "vote": "approve" OR "reject" OR "abstain",
  "confidence": <0-10>,
  "reasoning": "<razão principal em 1-2 frases>",
  "concerns": ["<concern1>", "<concern2>"]
}}

Critérios: approve se benefício > risco. reject se risco crítico. abstain se insuficiente contexto."""


# ── Council ────────────────────────────────────────────────────────────────────

class MultiAgentCouncil:
    """
    Conselho de 4 agentes que revê patches antes de aplicar.
    """

    MEMBERS = [
        ("arquiteto",  "Arquitecto"),
        ("programador", "Programador"),
        ("testador",   "Testador"),
        ("revisor",    "Revisor"),
    ]

    # Patches simples que não precisam de LLM (apenas validação local)
    SIMPLE_PATTERNS = [
        "docstring", "comment", "#", "logger.", "log.", "print(",
        "# TODO", "# FIXME", ".md", "README",
    ]

    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.base_url = Config.DEEPSEEK_BASE_URL
        self._log: list[dict] = []

    def review(self, patch: dict, dry_run: bool = False) -> CouncilDecision:
        """
        Revê um patch com o conselho completo.
        Se dry_run=True, simula sem custo de API (usa heurísticas locais).
        """
        desc = patch.get("description", "sem descrição")
        target = patch.get("target_file", "?")
        decision = CouncilDecision(patch_description=desc, patch_file=target)

        # Patches simples: só validação local (zero API)
        if self._is_simple_patch(patch) or dry_run:
            return self._local_review(patch, decision)

        # Ler conteúdo do ficheiro para contexto
        file_content = self._read_file(target)

        # Votos de cada membro
        for role_id, role_name in self.MEMBERS:
            vote = self._get_vote(role_id, role_name, patch, file_content)
            decision.votes.append(vote)
            logger.info(
                f"[Council] {role_name}: {vote.vote} "
                f"(confidence={vote.confidence}) — {vote.reasoning[:60]}"
            )

            # Veto automático: arquitecto rejeita com alta confiança
            if role_id == "arquiteto" and vote.vote == "reject" and vote.confidence >= 8:
                decision.veto = True
                decision.approved = False
                decision.final_reasoning = f"VETO do Arquitecto: {vote.reasoning}"
                self._log_decision(decision)
                return decision

        # Decisão por maioria
        decision.approved = decision.approve_count >= 3
        concerns = []
        for v in decision.votes:
            concerns.extend(v.concerns)

        if decision.approved:
            decision.final_reasoning = (
                f"Aprovado {decision.approve_count}/4. "
                + (f"Preocupações menores: {'; '.join(concerns[:2])}" if concerns else "Sem preocupações.")
            )
        else:
            decision.final_reasoning = (
                f"Rejeitado {decision.reject_count}/4. "
                + (f"Razões: {'; '.join(concerns[:3])}" if concerns else "Benefício insuficiente.")
            )

        self._log_decision(decision)
        logger.info(f"[Council] {decision.summary()}")
        return decision

    def _get_vote(
        self,
        role_id: str,
        role_name: str,
        patch: dict,
        file_content: str,
    ) -> MemberVote:
        """Chama o LLM para obter voto de um membro."""
        prompt = _member_prompt(role_id, patch, file_content)
        try:
            import urllib.request
            payload = json.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.2,
            }).encode()
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
                content = data["choices"][0]["message"]["content"].strip()

            # Limpar markdown se o LLM o incluiu
            content = content.replace("```json", "").replace("```", "").strip()
            vote_data = json.loads(content)

            return MemberVote(
                member=role_name,
                role=role_id,
                vote=vote_data.get("vote", "abstain"),
                confidence=int(vote_data.get("confidence", 5)),
                reasoning=vote_data.get("reasoning", "")[:200],
                concerns=vote_data.get("concerns", [])[:3],
            )
        except Exception as e:
            logger.warning(f"[Council] {role_name} falhou: {e}")
            # Abstém em caso de erro
            return MemberVote(
                member=role_name, role=role_id,
                vote="abstain", confidence=0,
                reasoning=f"Erro ao obter voto: {e}",
            )

    def _is_simple_patch(self, patch: dict) -> bool:
        """True se o patch é simples o suficiente para validação local."""
        replacement = patch.get("replacement", "")
        search = patch.get("search_str", "")
        target = patch.get("target_file", "")
        # Só docs/comments ou ficheiros não-Python
        if not target.endswith(".py"):
            return True
        combined = (replacement + search).lower()
        return any(p in combined for p in self.SIMPLE_PATTERNS) and len(replacement) < 100

    def _local_review(self, patch: dict, decision: CouncilDecision) -> CouncilDecision:
        """Revisão local rápida sem LLM."""
        decision.local_only = True
        from evolution.patch_validator import PatchValidator
        validator = PatchValidator()
        result = validator.validate(patch)
        decision.approved = result.get("valid", False)
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        decision.final_reasoning = (
            "Validação local: " +
            ("; ".join(errors) if errors else "OK") +
            (f" [avisos: {'; '.join(warnings[:2])}]" if warnings else "")
        )
        self._log_decision(decision)
        return decision

    def _read_file(self, target: str) -> str:
        """Lê as primeiras 200 linhas do ficheiro alvo."""
        try:
            path = Config.REPO_LOCAL_PATH / target
            if path.exists():
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[:200])
        except Exception:
            pass
        return "(ficheiro não encontrado)"

    def _log_decision(self, decision: CouncilDecision) -> None:
        """Persiste decisão no log."""
        try:
            _COUNCIL_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(_COUNCIL_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision.to_dict(), ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    def recent_decisions(self, limit: int = 20) -> list[dict]:
        """Últimas decisões do conselho."""
        decisions = []
        try:
            if _COUNCIL_LOG.exists():
                lines = _COUNCIL_LOG.read_text(encoding="utf-8").splitlines()
                for line in reversed(lines[-limit:]):
                    if line.strip():
                        decisions.append(json.loads(line))
        except Exception:
            pass
        return decisions

    def stats(self) -> dict:
        decisions = self.recent_decisions(limit=1000)
        total = len(decisions)
        approved = sum(1 for d in decisions if d.get("approved"))
        vetoed = sum(1 for d in decisions if d.get("veto"))
        return {
            "total_reviewed": total,
            "approved": approved,
            "rejected": total - approved,
            "vetoed": vetoed,
            "approval_rate": round(approved / total * 100, 1) if total else 0,
        }


# Singleton
_council: Optional[MultiAgentCouncil] = None

def get_council() -> MultiAgentCouncil:
    global _council
    if _council is None:
        _council = MultiAgentCouncil()
    return _council
