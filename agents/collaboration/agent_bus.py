"""
agents/collaboration/agent_bus.py — Bus de mensagens entre agentes.

Permite que agentes comuniquem, partilhem descobertas e colaborem
sem estarem no mesmo processo ou thread.

Tipos de mensagem:
  IDEA        — brainstormer propõe ideia para discussão
  CRITIQUE    — agente critica ou melhora ideia de outro
  KNOWLEDGE   — agente partilha descoberta/aprendizagem
  TASK_REQUEST — agente pede ajuda a especialista
  CONSENSUS   — votação sobre decisão colectiva
  INSIGHT     — padrão detectado na memória/logs

Persistência: memory/agent_messages.jsonl (append-only)
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

_MSG_FILE = Path("memory") / "agent_messages.jsonl"
_MAX_READ  = 200   # mensagens mais recentes a carregar


class MsgType:
    IDEA         = "idea"
    CRITIQUE     = "critique"
    KNOWLEDGE    = "knowledge"
    TASK_REQUEST = "task_request"
    CONSENSUS    = "consensus"
    INSIGHT      = "insight"
    REPLY        = "reply"


@dataclass
class AgentMessage:
    sender:    str          # nome do agente que envia
    msg_type:  str          # MsgType.*
    content:   str          # conteúdo da mensagem
    topic:     str = ""     # tópico/thread (para agrupar)
    reply_to:  str = ""     # id de mensagem a que responde
    msg_id:    str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    votes:     dict = field(default_factory=dict)   # {agent: "approve"/"reject"}
    metadata:  dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def short(self) -> str:
        return f"[{self.sender}→{self.msg_type}] {self.content[:80]}"


class AgentBus:
    """Bus persistente de comunicação entre agentes."""

    def publish(self, msg: AgentMessage) -> str:
        """Publica mensagem. Retorna msg_id."""
        _MSG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_MSG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg.to_dict(), ensure_ascii=False, default=str) + "\n")
        return msg.msg_id

    def send(
        self,
        sender: str,
        msg_type: str,
        content: str,
        topic: str = "",
        reply_to: str = "",
        metadata: dict = None,
    ) -> str:
        """Atalho para criar e publicar mensagem."""
        msg = AgentMessage(
            sender=sender,
            msg_type=msg_type,
            content=content,
            topic=topic,
            reply_to=reply_to,
            metadata=metadata or {},
        )
        return self.publish(msg)

    def read_recent(self, limit: int = _MAX_READ, topic: str = "") -> list[AgentMessage]:
        """Lê mensagens recentes, opcionalmente filtradas por tópico."""
        if not _MSG_FILE.exists():
            return []
        msgs = []
        try:
            lines = _MSG_FILE.read_text(encoding="utf-8").splitlines()
            for line in lines[-limit * 2:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if topic and d.get("topic") != topic:
                        continue
                    msgs.append(AgentMessage(**{
                        k: v for k, v in d.items()
                        if k in AgentMessage.__dataclass_fields__
                    }))
                except Exception:
                    pass
        except Exception:
            pass
        return msgs[-limit:]

    def read_thread(self, topic: str, limit: int = 50) -> list[AgentMessage]:
        """Lê toda a thread de um tópico."""
        return self.read_recent(limit=limit, topic=topic)

    def get_unread_for(self, agent: str, since_hours: int = 24) -> list[AgentMessage]:
        """Mensagens recentes que o agente ainda não respondeu."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=since_hours)).isoformat()
        recent = self.read_recent(limit=100)
        return [
            m for m in recent
            if m.sender != agent           # não as do próprio
            and m.timestamp >= cutoff
            and m.msg_type in (MsgType.IDEA, MsgType.KNOWLEDGE, MsgType.TASK_REQUEST)
        ]

    def vote(self, agent: str, msg_id: str, vote: str) -> None:
        """Regista voto numa mensagem de consenso (append nova mensagem de voto)."""
        self.send(
            sender=agent,
            msg_type=MsgType.CONSENSUS,
            content=f"Voto: {vote}",
            reply_to=msg_id,
            metadata={"vote": vote, "on_msg": msg_id},
        )

    def get_votes(self, msg_id: str) -> dict[str, str]:
        """Retorna votos registados para uma mensagem."""
        all_msgs = self.read_recent(limit=200)
        votes = {}
        for m in all_msgs:
            if m.reply_to == msg_id and m.msg_type == MsgType.CONSENSUS:
                votes[m.sender] = m.metadata.get("vote", "")
        return votes

    def format_for_prompt(self, msgs: list[AgentMessage], max_chars: int = 1500) -> str:
        """Formata mensagens para injectar num prompt."""
        if not msgs:
            return ""
        lines = ["## MENSAGENS DOS OUTROS AGENTES (lidas antes de responder)"]
        total = 0
        for m in msgs:
            line = f"- [{m.timestamp[:16]}] {m.sender} ({m.msg_type}): {m.content[:200]}"
            total += len(line)
            if total > max_chars:
                break
            lines.append(line)
        return "\n".join(lines)


# Singleton
_bus = AgentBus()

def get_agent_bus() -> AgentBus:
    return _bus
