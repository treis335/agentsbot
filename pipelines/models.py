"""
pipelines/models.py — Modelos para pipelines multi-agente.

Inspirado no Mission Control:
- Pipeline = sequencia de passos
- Cada passo e executado por um agente diferente
- O output de um passo e input do proximo
- Quality gate entre passos
"""
import uuid
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class PipelineStep:
    """Um passo dentro de um pipeline."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    agent_role: str = ""  # Que tipo de agente executa
    task_template: str = ""  # Template da tarefa
    depends_on: list[str] = field(default_factory=list)  # IDs de passos anteriores
    status: PipelineStatus = PipelineStatus.PENDING
    result: str = ""
    task_id: str = ""  # ID da tarefa criada
    order: int = 0


@dataclass
class Pipeline:
    """Pipeline multi-agente."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: list[PipelineStep] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "agent_role": s.agent_role,
                    "task_template": s.task_template,
                    "depends_on": s.depends_on,
                    "status": s.status.value,
                    "result": s.result,
                    "task_id": s.task_id,
                    "order": s.order,
                }
                for s in self.steps
            ],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
