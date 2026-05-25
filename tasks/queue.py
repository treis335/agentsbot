"""
tasks/queue.py — Fila de tarefas com prioridade e distribuicao.

Inspirado no Mission Control:
- Queue-based dispatch
- Prioridade + antiguidade
- Capacidade maxima por agente
- Ciclo de vida completo
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config
from core.bus import bus
from .models import Task, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Fila de tarefas com prioridade.

    Uso:
        queue = TaskQueue()
        task = queue.create_task("Fix bug", "O login nao funciona...")
        queue.assign(task.id, "agent_id")
        await queue.process_next("agent_id")
    """

    def __init__(self):
        self.config = Config
        self.tasks: dict[str, Task] = {}
        self._load()

    def _load(self) -> None:
        """Carrega tarefas do ficheiro."""
        tasks_file = self.config.TASKS_FILE
        if not tasks_file.exists():
            logger.info("[TaskQueue] Nenhuma tarefa encontrada.")
            return
        try:
            data = json.loads(tasks_file.read_text(encoding="utf-8"))
            for item in data:
                task = Task.from_dict(item)
                self.tasks[task.id] = task
            logger.info(f"[TaskQueue] {len(self.tasks)} tarefa(s) carregada(s).")
        except Exception as e:
            logger.error(f"[TaskQueue] Erro ao carregar: {e}")

    def _save(self) -> None:
        """Guarda tarefas no ficheiro."""
        self.config.TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.config.TASKS_FILE.write_text(
            json.dumps([t.to_dict() for t in self.tasks.values()], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # --- API Publica ---

    def create_task(self, title: str, description: str = "",
                    priority: TaskPriority = TaskPriority.MEDIUM,
                    created_by: str = "system",
                    tags: list[str] | None = None) -> Task:
        """Cria uma nova tarefa na fila (status=inbox)."""
        task = Task(
            title=title,
            description=description,
            priority=priority,
            created_by=created_by,
            tags=tags or [],
        )
        self.tasks[task.id] = task
        self._save()
        logger.info(f"[TaskQueue] Tarefa criada: {title} ({task.id[:8]})")
        return task

    def assign(self, task_id: str, agent_id: str) -> bool:
        """Atribui tarefa a um agente (status=assigned)."""
        task = self._get(task_id)
        if not task:
            return False
        task.assigned_to = agent_id
        task.status = TaskStatus.ASSIGNED
        task.updated_at = datetime.now().isoformat()
        self._save()
        logger.info(f"[TaskQueue] Tarefa {task.id[:8]} atribuida a {agent_id[:8]}")
        return True

    def start(self, task_id: str) -> bool:
        """Marca tarefa como em progresso."""
        task = self._get(task_id)
        if not task:
            return False
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def complete(self, task_id: str, result: str = "") -> bool:
        """Marca tarefa como concluida."""
        task = self._get(task_id)
        if not task:
            return False
        task.status = TaskStatus.DONE
        task.result = result
        task.updated_at = datetime.now().isoformat()
        self._save()
        logger.info(f"[TaskQueue] Tarefa concluida: {task.title}")
        return True

    def fail(self, task_id: str, error: str = "") -> bool:
        """Marca tarefa como falhada."""
        task = self._get(task_id)
        if not task:
            return False
        task.status = TaskStatus.FAILED
        task.result = error
        task.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def cancel(self, task_id: str) -> bool:
        """Cancela uma tarefa."""
        task = self._get(task_id)
        if not task:
            return False
        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def get_next_for_agent(self, agent_id: str) -> Optional[Task]:
        """
        Obtem a proxima tarefa para um agente (queue-based dispatch).

        Ordem: prioridade (critical > high > medium > low) > criacao (FIFO)
        """
        available = [
            t for t in self.tasks.values()
            if t.status == TaskStatus.INBOX
        ]
        if not available:
            return None

        # Ordenar por prioridade e antiguidade
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        available.sort(key=lambda t: (priority_order.get(t.priority, 99), t.created_at))

        best = available[0]
        self.assign(best.id, agent_id)
        return best

    def list_tasks(self, status: Optional[TaskStatus] = None) -> list[Task]:
        """Lista tarefas, opcionalmente filtradas por estado."""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def _get(self, task_id: str) -> Optional[Task]:
        """Busca tarefa por ID completo ou prefixo."""
        if task_id in self.tasks:
            return self.tasks[task_id]
        for t in self.tasks.values():
            if t.id.startswith(task_id):
                return t
        return None
