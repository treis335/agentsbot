"""
core/priority_queue.py — Fila prioritária para tarefas do utilizador.

Tarefas do Telegram são colocadas aqui e executadas IMEDIATAMENTE,
sem esperar pelo ciclo de auto-evolução (que pode demorar 120s+).

O loop autónomo verifica esta fila ANTES de dormir — se houver
algo aqui, processa imediatamente.

Dois tipos de tarefas:
  - USER: vem do Telegram, executa imediatamente, notifica quando pronto
  - AUTO: auto-evolução, executa no ritmo do ciclo (económico)
"""
import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_QUEUE_FILE = Path("memory") / "priority_queue.json"
_lock = threading.Lock()


@dataclass
class PriorityTask:
    id: str
    title: str
    description: str
    source: str           # "user" | "auto"
    priority: int = 1     # 1 = máxima, 10 = mínima
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    user_id: int = 0      # Telegram user_id para notificação
    status: str = "pending"
    result: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class PriorityQueue:
    """
    Fila de tarefas com dois níveis:
    - Nível USER (prioridade 1-3): executa imediatamente, sem esperar ciclo
    - Nível AUTO (prioridade 4-10): executa no ritmo do ciclo económico

    Thread-safe — pode ser acedida pelo loop autónomo e pelo handler do Telegram.
    """

    def __init__(self):
        self._tasks: list[PriorityTask] = []
        self._notify_cb: Optional[Callable] = None  # callback para notificar quando tarefa user completa
        self._load()

    def add_user_task(self, title: str, description: str,
                      user_id: int = 0, priority: int = 1) -> PriorityTask:
        """
        Adiciona tarefa do utilizador — executa imediatamente.
        Retorna a tarefa criada (com id para tracking).
        """
        task = PriorityTask(
            id=f"user_{int(time.time())}",
            title=title,
            description=description,
            source="user",
            priority=min(priority, 3),  # user tasks são sempre prioridade alta
            user_id=user_id,
        )
        with _lock:
            self._tasks.append(task)
            self._save()
        logger.info(f"[PriorityQueue] 👤 Tarefa do utilizador: {title[:60]}")
        return task

    def add_auto_task(self, title: str, description: str,
                      priority: int = 5) -> PriorityTask:
        """Adiciona tarefa de auto-evolução — executa no ritmo do ciclo."""
        task = PriorityTask(
            id=f"auto_{int(time.time())}",
            title=title,
            description=description,
            source="auto",
            priority=max(priority, 4),  # auto tasks nunca têm prioridade máxima
        )
        with _lock:
            self._tasks.append(task)
            self._save()
        return task

    def get_next(self) -> Optional[PriorityTask]:
        """
        Retorna a próxima tarefa pendente por prioridade.
        Tarefas USER (1-3) sempre antes de AUTO (4-10).
        """
        with _lock:
            pending = [t for t in self._tasks if t.status == "pending"]
            if not pending:
                return None
            return min(pending, key=lambda t: (t.priority, t.created_at))

    def get_next_user_task(self) -> Optional[PriorityTask]:
        """Retorna a próxima tarefa do utilizador (se houver)."""
        with _lock:
            user_pending = [t for t in self._tasks
                           if t.status == "pending" and t.source == "user"]
            if not user_pending:
                return None
            return min(user_pending, key=lambda t: t.created_at)

    def has_user_tasks(self) -> bool:
        """Verifica se há tarefas do utilizador pendentes."""
        with _lock:
            return any(t.status == "pending" and t.source == "user"
                      for t in self._tasks)

    def mark_done(self, task_id: str, result: str = "") -> None:
        with _lock:
            for t in self._tasks:
                if t.id == task_id:
                    t.status = "done"
                    t.result = result[:500]
                    t.completed_at = datetime.now().isoformat()
            self._save()

    def mark_failed(self, task_id: str, error: str = "") -> None:
        with _lock:
            for t in self._tasks:
                if t.id == task_id:
                    t.status = "failed"
                    t.result = error[:300]
                    t.completed_at = datetime.now().isoformat()
            self._save()

    def set_notify_callback(self, cb: Callable) -> None:
        """Registar callback para notificar o utilizador quando tarefa completa."""
        self._notify_cb = cb

    async def notify_user(self, task: PriorityTask) -> None:
        """Notifica o utilizador via Telegram quando a sua tarefa completa."""
        if not self._notify_cb or not task.user_id:
            return
        try:
            status_icon = "✅" if task.status == "done" else "❌"
            msg = (
                f"{status_icon} **Tarefa concluída:** {task.title}\n\n"
                f"{task.result[:400]}"
            )
            await self._notify_cb(task.user_id, msg)
        except Exception as e:
            logger.debug(f"[PriorityQueue] Notificação falhou: {e}")

    def stats(self) -> dict:
        with _lock:
            user_pending = sum(1 for t in self._tasks if t.status == "pending" and t.source == "user")
            auto_pending = sum(1 for t in self._tasks if t.status == "pending" and t.source == "auto")
            done = sum(1 for t in self._tasks if t.status == "done")
            return {"user_pending": user_pending, "auto_pending": auto_pending, "done": done}

    def _load(self):
        if _QUEUE_FILE.exists():
            try:
                data = json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
                self._tasks = [
                    PriorityTask(**{k: v for k, v in d.items()
                                    if k in PriorityTask.__dataclass_fields__})
                    for d in data
                ]
                # Limpar tarefas antigas concluídas (manter só últimas 50)
                done = [t for t in self._tasks if t.status in ("done", "failed")]
                pending = [t for t in self._tasks if t.status == "pending"]
                self._tasks = pending + done[-50:]
            except Exception:
                self._tasks = []

    def _save(self):
        try:
            _QUEUE_FILE.parent.mkdir(exist_ok=True)
            _QUEUE_FILE.write_text(
                json.dumps([t.to_dict() for t in self._tasks],
                           indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"[PriorityQueue] Erro ao guardar: {e}")


# Instância global
_queue: Optional[PriorityQueue] = None

def get_priority_queue() -> PriorityQueue:
    global _queue
    if _queue is None:
        _queue = PriorityQueue()
    return _queue
