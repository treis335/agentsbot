"""
soul/soul_system.py — Sistema de Alma do ecossistema.

A identidade persistente do ecossistema — quem é, como pensa,
o que valoriza, como comunica. Evolui lentamente e com controlo.

A alma NÃO é alterada automaticamente pelos agentes.
Só pode ser actualizada com aprovação explícita (Governance Layer).

Sprint 4 do Evolution Roadmap.
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SOUL_FILE       = Path("soul") / "soul_profile.json"
SOUL_HISTORY    = Path("soul") / "soul_history.jsonl"
SOUL_PROPOSALS  = Path("soul") / "proposals.json"

Path("soul").mkdir(exist_ok=True)


@dataclass
class SoulProfile:
    """A identidade completa do ecossistema."""

    # Comunicação
    communication_style: str = "técnico-directo"  # técnico-directo, conversacional, formal
    verbosity: str = "médio"                       # conciso, médio, detalhado
    humor: str = "baixo"                           # nenhum, baixo, moderado
    language: str = "português europeu"

    # Personalidade
    proactivity: str = "alto"          # baixo, médio, alto
    curiosity: str = "alto"
    risk_tolerance: str = "moderado"   # conservador, moderado, arrojado
    creativity: str = "alto"

    # Valores
    ethics: list = field(default_factory=lambda: [
        "transparência total com o utilizador",
        "nunca destruir código funcional sem backup",
        "preferir soluções simples a complexas",
        "admitir erros e aprender com eles",
        "proteger dados e privacidade",
    ])

    # Missão
    mission: str = "Construir negócios reais e autónomos que gerem valor para o utilizador"
    vision: str  = "Ser o ecossistema de IA mais capaz e fiável do utilizador"

    # Preferências de aprendizagem
    learn_from_failures: bool = True
    prefer_proven_patterns: bool = True
    experiment_in_sandbox: bool = True

    # Metadados
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    update_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt_injection(self) -> str:
        """Formata para injectar no system prompt de qualquer agente."""
        return f"""## ALMA DO ECOSSISTEMA
Estilo: {self.communication_style} | Verbosidade: {self.verbosity}
Proactividade: {self.proactivity} | Criatividade: {self.creativity}
Tolerância ao risco: {self.risk_tolerance}
Missão: {self.mission}
Valores: {' • '.join(self.ethics[:3])}"""


@dataclass
class SoulProposal:
    """Proposta de alteração à alma — precisa de aprovação."""
    id: str
    field_name: str
    current_value: str
    proposed_value: str
    reason: str
    proposed_by: str
    proposed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"   # pending, approved, rejected
    reviewed_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class SoulSystem:
    """
    Gere a identidade persistente do ecossistema.

    A alma injeta contexto em todos os agentes e evolui
    de forma controlada através de propostas aprovadas.
    """

    def __init__(self):
        self._profile: Optional[SoulProfile] = None
        self._proposals: list[SoulProposal] = []
        self._load()

    def get_profile(self) -> SoulProfile:
        if self._profile is None:
            self._profile = SoulProfile()
            self._save()
        return self._profile

    def inject_into_prompt(self, prompt: str) -> str:
        """Adiciona o contexto da alma a qualquer system prompt."""
        soul_ctx = self.get_profile().to_prompt_injection()
        return soul_ctx + "\n\n" + prompt

    def propose_change(self, field_name: str, new_value: str,
                       reason: str, proposed_by: str = "auto_evolver") -> str:
        """
        Propõe uma alteração à alma.
        NÃO aplica directamente — vai para aprovação.
        """
        profile = self.get_profile()
        if not hasattr(profile, field_name):
            return f"Campo '{field_name}' não existe na alma."

        current = str(getattr(profile, field_name))
        proposal = SoulProposal(
            id=f"soul_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            field_name=field_name,
            current_value=current,
            proposed_value=new_value,
            reason=reason,
            proposed_by=proposed_by,
        )
        self._proposals.append(proposal)
        self._save_proposals()
        logger.info(f"[SoulSystem] Proposta: {field_name}: '{current}' → '{new_value}'")
        return f"✅ Proposta registada (id={proposal.id}). Aguarda aprovação."

    def approve_proposal(self, proposal_id: str) -> str:
        """Aprova e aplica uma proposta de alteração à alma."""
        for p in self._proposals:
            if p.id == proposal_id and p.status == "pending":
                profile = self.get_profile()
                old_val = getattr(profile, p.field_name, None)
                try:
                    # Tentar converter para o tipo correcto
                    new_val = type(old_val)(p.proposed_value) if old_val is not None else p.proposed_value
                    setattr(profile, p.field_name, new_val)
                except Exception:
                    setattr(profile, p.field_name, p.proposed_value)

                profile.last_updated = datetime.now().isoformat()
                profile.update_count += 1
                p.status = "approved"
                p.reviewed_at = datetime.now().isoformat()

                self._save()
                self._save_proposals()
                self._log_history(p, "approved")
                return f"✅ Alma actualizada: {p.field_name} = '{p.proposed_value}'"
        return f"Proposta {proposal_id} não encontrada ou já processada."

    def reject_proposal(self, proposal_id: str) -> str:
        """Rejeita uma proposta."""
        for p in self._proposals:
            if p.id == proposal_id and p.status == "pending":
                p.status = "rejected"
                p.reviewed_at = datetime.now().isoformat()
                self._save_proposals()
                return f"Proposta {proposal_id} rejeitada."
        return f"Proposta {proposal_id} não encontrada."

    def get_pending_proposals(self) -> list[SoulProposal]:
        return [p for p in self._proposals if p.status == "pending"]

    def get_summary(self) -> str:
        """Resumo legível da alma actual."""
        p = self.get_profile()
        lines = [
            f"🧬 **Alma v{p.version}** (actualizada {p.update_count}x)",
            f"📣 Estilo: {p.communication_style} | Verbosidade: {p.verbosity}",
            f"🧠 Proactividade: {p.proactivity} | Criatividade: {p.creativity}",
            f"🎯 Missão: {p.mission}",
            f"⚖️  Valores: {' • '.join(p.ethics[:2])}",
        ]
        pending = len(self.get_pending_proposals())
        if pending:
            lines.append(f"⏳ {pending} proposta(s) de evolução pendente(s)")
        return "\n".join(lines)

    def _load(self):
        try:
            if SOUL_FILE.exists():
                data = json.loads(SOUL_FILE.read_text(encoding="utf-8"))
                self._profile = SoulProfile(**{
                    k: v for k, v in data.items()
                    if k in SoulProfile.__dataclass_fields__
                })
        except Exception:
            self._profile = SoulProfile()

        try:
            if SOUL_PROPOSALS.exists():
                data = json.loads(SOUL_PROPOSALS.read_text(encoding="utf-8"))
                self._proposals = [
                    SoulProposal(**{k: v for k, v in d.items()
                                    if k in SoulProposal.__dataclass_fields__})
                    for d in data
                ]
        except Exception:
            pass

    def _save(self):
        SOUL_FILE.write_text(
            json.dumps(self.get_profile().to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _save_proposals(self):
        SOUL_PROPOSALS.write_text(
            json.dumps([p.to_dict() for p in self._proposals], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _log_history(self, proposal: SoulProposal, action: str):
        try:
            with open(SOUL_HISTORY, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": datetime.now().isoformat(),
                    "action": action,
                    "proposal": proposal.to_dict(),
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass


# Instância global
_soul: Optional[SoulSystem] = None

def get_soul() -> SoulSystem:
    global _soul
    if _soul is None:
        _soul = SoulSystem()
    return _soul
