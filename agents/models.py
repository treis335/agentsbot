"""
agents/models.py — Modelos de dados para agentes.

Define a estrutura base de um agente com todos os campos
necessarios para operacao autonoma.
"""
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AgentStatus(Enum):
    """Estados possiveis de um agente."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    SLEEPING = "sleeping"


class AgentRole(Enum):
    """Papeis pre-definidos para agentes."""
    SUPERVISOR = "supervisor"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    ARCHITECT = "architect"
    RESEARCHER = "researcher"
    DEVOPS = "devops"
    DOCUMENTER = "documenter"
    EXPLORER = "explorer"
    OPTIMIZER = "optimizer"
    CUSTOM = "custom"


@dataclass
class Agent:
    """
    Representacao completa de um agente.

    Atributos:
        id: UUID unico
        name: Nome legivel
        role: Papel/funcao
        soul: Personalidade (system prompt)
        model: Modelo LLM
        status: Estado atual
        capabilities: Lista de capacidades
        context: Historico de conversa
        metadata: Dados extras (config, tags, etc.)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: AgentRole = AgentRole.CUSTOM
    soul: str = ""
    model: str = "deepseek-chat"
    status: AgentStatus = AgentStatus.IDLE
    capabilities: list[str] = field(default_factory=list)
    context: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    last_active: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "soul": self.soul,
            "model": self.model,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "context": [],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            role=AgentRole(data.get("role", "custom")),
            soul=data.get("soul", ""),
            model=data.get("model", "deepseek-chat"),
            status=AgentStatus(data.get("status", "idle")),
            capabilities=data.get("capabilities", []),
            context=data.get("context", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            last_active=data.get("last_active", ""),
        )

    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.id[:8]}) [{self.status.value}]>"
