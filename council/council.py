"""
council/council.py — Conselho Multi-Agente para Governança.

Antes de qualquer patch ser aplicado ao sistema, 4 agentes revisam
e votam. Maioria simples (3/4) para aprovar.

Agentes do Conselho:
  🏗️  Architect  — avalia coerência e impacto global
  💻  Engineer   — avalia código e arquitectura técnica
  🧪  Tester     — avalia edge cases e robustez
  🔒  Security   — avalia riscos e permissões
  📋  Reviewer   — produz relatório final e decide

Sprint 8 do Evolution Roadmap.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

COUNCIL_DIR     = Path("council")
DECISIONS_FILE  = COUNCIL_DIR / "decisions.jsonl"
COUNCIL_DIR.mkdir(exist_ok=True)

COUNCIL_MEMBERS = {
    "architect": {
        "emoji": "🏗️",
        "focus": "Avalia coerência arquitectural e impacto no sistema. Pergunta: isto encaixa na arquitectura actual? Há dependências quebradas? Vai criar dívida técnica?",
        "vote_weight": 1,
    },
    "engineer": {
        "emoji": "💻",
        "focus": "Avalia qualidade técnica do código. Pergunta: o código é limpo? Há bugs óbvios? Segue os padrões do projecto? Há casos extremos não tratados?",
        "vote_weight": 1,
    },
    "tester": {
        "emoji": "🧪",
        "focus": "Avalia robustez e testabilidade. Pergunta: como pode isto falhar? Há edge cases perigosos? O rollback é possível? Podemos verificar que funciona?",
        "vote_weight": 1,
    },
    "security": {
        "emoji": "🔒",
        "focus": "Avalia riscos de segurança. Pergunta: este código acede a recursos sensíveis? Pode ser explorado? Altera permissões? Expõe dados?",
        "vote_weight": 1,
    },
}

REVIEWER = {
    "emoji": "📋",
    "focus": "Sintetiza os votos e produz decisão final. Peso 0 — só decide em caso de empate.",
}


@dataclass
class CouncilVote:
    member: str
    vote: str          # approve | reject | needs_revision
    confidence: float  # 0.0 a 1.0
    reasoning: str
    concerns: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CouncilDecision:
    id: str
    patch_title: str
    patch_description: str
    patch_file: str
    patch_code_preview: str
    votes: list = field(default_factory=list)
    final_verdict: str = "pending"   # approve | reject | needs_revision
    final_reasoning: str = ""
    approved_count: int = 0
    rejected_count: int = 0
    revision_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    decided_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["votes"] = [v if isinstance(v, dict) else asdict(v) for v in self.votes]
        return d


class Council:
    """
    Conselho de governança multi-agente.
    Revê e vota patches antes de aplicar ao sistema.
    """

    # Threshold: quantos votos "approve" são necessários
    APPROVAL_THRESHOLD = 3  # de 4 membros

    def __init__(self):
        self._decisions: list[CouncilDecision] = []
        self._load()

    def review(self, patch: dict) -> CouncilDecision:
        """
        Submete um patch a revisão pelo conselho.
        Bloqueia até obter todos os votos.

        Args:
            patch: {
                "title": str,
                "description": str,
                "file": str,
                "code": str,
            }

        Returns:
            CouncilDecision com veredicto final
        """
        decision = CouncilDecision(
            id=f"council_{int(time.time())}",
            patch_title=patch.get("title", "Patch sem título"),
            patch_description=patch.get("description", ""),
            patch_file=patch.get("file", ""),
            patch_code_preview=patch.get("code", "")[:500],
        )

        logger.info(f"[Council] 🏛️  Revisão: {decision.patch_title}")

        # Correr votação
        loop = asyncio.new_event_loop()
        try:
            votes = loop.run_until_complete(self._collect_votes(patch, decision.id))
        finally:
            loop.close()

        decision.votes = [v.to_dict() for v in votes]
        decision.approved_count  = sum(1 for v in votes if v.vote == "approve")
        decision.rejected_count  = sum(1 for v in votes if v.vote == "reject")
        decision.revision_count  = sum(1 for v in votes if v.vote == "needs_revision")

        # Decisão final
        if decision.approved_count >= self.APPROVAL_THRESHOLD:
            decision.final_verdict   = "approve"
            decision.final_reasoning = self._summarise_approval(votes)
        elif decision.rejected_count >= 2:
            decision.final_verdict   = "reject"
            decision.final_reasoning = self._summarise_rejection(votes)
        else:
            decision.final_verdict   = "needs_revision"
            decision.final_reasoning = self._summarise_revision(votes)

        decision.decided_at = datetime.now().isoformat()
        self._decisions.append(decision)
        self._save(decision)

        icon = {"approve": "✅", "reject": "❌", "needs_revision": "🔄"}.get(
            decision.final_verdict, "?"
        )
        logger.info(
            f"[Council] {icon} {decision.final_verdict.upper()} "
            f"({decision.approved_count}✅ {decision.rejected_count}❌ {decision.revision_count}🔄)"
        )
        return decision

    async def _collect_votes(self, patch: dict, decision_id: str) -> list[CouncilVote]:
        """Recolhe votos de todos os membros do conselho em paralelo."""
        tasks = [
            self._get_vote(member, info, patch, decision_id)
            for member, info in COUNCIL_MEMBERS.items()
        ]
        votes = await asyncio.gather(*tasks, return_exceptions=True)
        return [v for v in votes if isinstance(v, CouncilVote)]

    async def _get_vote(self, member: str, info: dict,
                        patch: dict, decision_id: str) -> CouncilVote:
        """Obtém voto de um membro do conselho."""
        from agents.llm_agent import _call_llm

        code_preview = patch.get("code", "")[:600]
        prompt = f"""És o {member} do Conselho de Governança do ecossistema agentsbot.

O teu foco: {info['focus']}

=== PATCH SUBMETIDO PARA REVISÃO ===
Título: {patch.get('title', '?')}
Ficheiro: {patch.get('file', '?')}
Descrição: {patch.get('description', '?')}

Código proposto (preview):
```python
{code_preview}
```

Analisa este patch com o teu foco específico e vota.

Responde APENAS em JSON:
{{
  "vote": "approve" | "reject" | "needs_revision",
  "confidence": 0.0-1.0,
  "reasoning": "razão principal em 1-2 frases",
  "concerns": ["preocupação 1", "preocupação 2"]
}}"""

        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _call_llm([{"role": "user", "content": prompt}],
                                   use_tools=False, max_tokens=300)
            )
            raw = resp["choices"][0]["message"].get("content", "{}").strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            data = json.loads(raw.strip())

            vote = CouncilVote(
                member=member,
                vote=data.get("vote", "needs_revision"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                concerns=data.get("concerns", []),
            )
            logger.info(
                f"[Council] {info['emoji']} {member}: {vote.vote} "
                f"(conf={vote.confidence:.1f}) — {vote.reasoning[:80]}"
            )
            return vote

        except Exception as e:
            logger.warning(f"[Council] {member} falhou: {e}")
            # Em caso de falha, voto neutro conservador
            return CouncilVote(
                member=member,
                vote="needs_revision",
                confidence=0.3,
                reasoning=f"Erro ao obter voto: {e}",
            )

    def _summarise_approval(self, votes: list[CouncilVote]) -> str:
        concerns = [c for v in votes for c in v.concerns if c]
        base = f"Aprovado por {sum(1 for v in votes if v.vote == 'approve')}/4 membros."
        if concerns:
            base += f" Atenção: {'; '.join(concerns[:2])}"
        return base

    def _summarise_rejection(self, votes: list[CouncilVote]) -> str:
        reasons = [v.reasoning for v in votes if v.vote == "reject"]
        return f"Rejeitado. Motivos: {' | '.join(reasons[:2])}"

    def _summarise_revision(self, votes: list[CouncilVote]) -> str:
        concerns = [c for v in votes for c in v.concerns if c]
        return f"Revisão necessária. Principais preocupações: {'; '.join(concerns[:3])}"

    def get_recent(self, n: int = 10) -> list[CouncilDecision]:
        return self._decisions[-n:]

    def get_stats(self) -> dict:
        total    = len(self._decisions)
        approved = sum(1 for d in self._decisions if d.final_verdict == "approve")
        rejected = sum(1 for d in self._decisions if d.final_verdict == "reject")
        revision = sum(1 for d in self._decisions if d.final_verdict == "needs_revision")
        return {
            "total": total, "approved": approved,
            "rejected": rejected, "revision": revision,
            "approval_rate": round(approved / total, 2) if total > 0 else 0.0,
        }

    def format_for_telegram(self, decision: CouncilDecision) -> str:
        icon = {"approve": "✅", "reject": "❌", "needs_revision": "🔄"}.get(
            decision.final_verdict, "?"
        )
        lines = [
            f"🏛️  **Conselho — {decision.patch_title}**",
            f"{icon} **{decision.final_verdict.upper()}** "
            f"({decision.approved_count}✅ {decision.rejected_count}❌)",
            "",
        ]
        for v in decision.votes:
            member_icon = COUNCIL_MEMBERS.get(v["member"] if isinstance(v, dict) else v.member,
                                              {}).get("emoji", "🤖")
            vote_val = v["vote"] if isinstance(v, dict) else v.vote
            reason   = v["reasoning"] if isinstance(v, dict) else v.reasoning
            vote_icon = {"approve": "✅", "reject": "❌", "needs_revision": "🔄"}.get(vote_val, "?")
            lines.append(f"{member_icon} {vote_icon} {reason[:80]}")

        lines += ["", f"💬 {decision.final_reasoning}"]
        return "\n".join(lines)

    def _load(self):
        if not DECISIONS_FILE.exists():
            return
        try:
            for line in DECISIONS_FILE.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    d = json.loads(line)
                    self._decisions.append(CouncilDecision(
                        **{k: v for k, v in d.items()
                           if k in CouncilDecision.__dataclass_fields__}
                    ))
        except Exception:
            pass

    def _save(self, decision: CouncilDecision):
        try:
            with open(DECISIONS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"[Council] Erro ao guardar decisão: {e}")


_council: Optional[Council] = None

def get_council() -> Council:
    global _council
    if _council is None:
        _council = Council()
    return _council
