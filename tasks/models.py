"""
tasks/models.py — Modelos de dados para tarefas.

Inspirado no Mission Control:
inbox -> assigned -> in_progress -> review -> done
"""
import uuid
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


class TaskStatus(Enum):
    """Estados do ciclo de vida de uma tarefa."""
    INBOX = "inbox"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Niveis de prioridade."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    """
    Representacao completa de uma tarefa.

    Atributos:
        id: UUID unico
        title: Titulo curto
        description: Descricao detalhada
        priority: Prioridade
        status: Estado atual
        assigned_to: ID do agente responsavel
        created_by: Quem criou (user_id ou "system")
        pipeline: Nome do pipeline (se aplicavel)
        parent_id: ID da tarefa pai (sub-tarefa)
        result: Resultado final
        feedback: Feedback da revisao
        tags: Etiquetas para categorizacao
        created_at: Timestamp de criacao
        updated_at: Timestamp de ultima atualizacao
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.INBOX
    assigned_to: str = ""
    created_by: str = "system"
    pipeline: str = ""
    parent_id: str = ""
    result: str = ""
    feedback: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "pipeline": self.pipeline,
            "parent_id": self.parent_id,
            "result": self.result,
            "feedback": self.feedback,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=TaskPriority(data.get("priority", "medium")),
            status=TaskStatus(data.get("status", "inbox")),
            assigned_to=data.get("assigned_to", ""),
            created_by=data.get("created_by", "system"),
            pipeline=data.get("pipeline", ""),
            parent_id=data.get("parent_id", ""),
            result=data.get("result", ""),
            feedback=data.get("feedback", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )

    def __repr__(self) -> str:
        return f"<Task {self.title} [{self.status.value}]>"
