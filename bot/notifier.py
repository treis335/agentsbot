"""
bot/notifier.py — Hub central de notificações proactivas.

Singleton global que qualquer módulo pode usar para enviar mensagens
ao owner sem precisar de ter acesso ao bot Telegram directamente.

Funciona como uma fila — se o bot ainda não está pronto, as mensagens
ficam em fila e são enviadas quando o bot ligar.

Uso em qualquer módulo:
    from bot.notifier import notify
    await notify("[OK] Tarefa completada: implementei o módulo X")
    notify_sync("[FIX] A correr auto-melhoria...")  # versão síncrona

Tipos de notificação configuráveis no .env:
    NOTIFY_ON_TASK_COMPLETE=true   (default: true)
    NOTIFY_ON_TASK_FAIL=true       (default: true)
    NOTIFY_ON_SELF_IMPROVE=true    (default: true)
    NOTIFY_DAILY_SUMMARY=true      (default: true)
    NOTIFY_DAILY_SUMMARY_HOUR=8    (hora do resumo diário)
"""

import asyncio
import logging
import threading
from collections import deque
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class Notifier:
    """
    Hub singleton de notificações Telegram proactivas.

    Thread-safe — pode ser chamado de threads ou coroutines.
    """

    def __init__(self):
        self._bot = None                      # telegram.Bot instance
        self._owner_id: Optional[int] = None
        self._queue: deque = deque(maxlen=50) # mensagens em fila
        self._lock = threading.Lock()
        self._last_summary_date: Optional[date] = None
        self._daily_stats = {"tasks_done": 0, "tasks_failed": 0, "improvements": 0}

        # Carregar configurações
        self._on_complete  = _env_bool("NOTIFY_ON_TASK_COMPLETE", True)
        self._on_fail      = _env_bool("NOTIFY_ON_TASK_FAIL", True)
        self._on_improve   = _env_bool("NOTIFY_ON_SELF_IMPROVE", True)
        self._daily        = _env_bool("NOTIFY_DAILY_SUMMARY", True)
        self._summary_hour = int(getattr(Config, "NOTIFY_DAILY_SUMMARY_HOUR", 8))

    def set_bot(self, bot, owner_id: int) -> None:
        """Registar o bot Telegram. Chamado do main.py após init_telegram()."""
        self._bot = bot
        self._owner_id = owner_id
        logger.info(f"[Notifier] Bot registado. Owner: {owner_id}")
        # Enviar mensagens que ficaram em fila
        if self._queue:
            asyncio.create_task(self._flush_queue())

    # ── Interface pública ──────────────────────────────────────────────────────

    async def send(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Envia mensagem ao owner. Retorna True se enviado."""
        if not self._bot or not self._owner_id:
            # Guardar em fila para enviar quando bot ligar
            with self._lock:
                self._queue.append((text, parse_mode))
            return False
        try:
            await self._bot.send_message(
                chat_id=self._owner_id,
                text=text,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.warning(f"[Notifier] Falhou envio: {e}")
            return False

    def send_sync(self, text: str) -> None:
        """Versão síncrona — coloca na fila e tenta enviar."""
        with self._lock:
            self._queue.append((text, "Markdown"))
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._flush_queue())
        except Exception:
            pass

    async def _flush_queue(self) -> None:
        """Envia todas as mensagens em fila."""
        while self._queue:
            with self._lock:
                if not self._queue:
                    break
                text, parse_mode = self._queue.popleft()
            await self.send(text, parse_mode)
            await asyncio.sleep(0.3)  # evitar rate limit

    # ── Notificações específicas ───────────────────────────────────────────────

    async def task_completed(self, title: str, agent: str, result: str) -> None:
        """Notifica conclusão de tarefa (se NOTIFY_ON_TASK_COMPLETE=true)."""
        self._daily_stats["tasks_done"] += 1
        if not self._on_complete:
            return
        short_result = str(result)[:200].replace("*", "").replace("`", "")
        msg = (
            f"[OK] *Tarefa concluída*\n\n"
            f"[LISTA] {title[:80]}\n"
            f"[IA] Agente: `{agent}`\n"
            f"[HORA] {datetime.now().strftime('%H:%M')}\n\n"
            f"_{short_result}_"
        )
        await self.send(msg)

    async def task_failed(self, title: str, agent: str, error: str) -> None:
        """Notifica falha de tarefa (se NOTIFY_ON_TASK_FAIL=true)."""
        self._daily_stats["tasks_failed"] += 1
        if not self._on_fail:
            return
        short_err = str(error)[:150].replace("*", "").replace("`", "")
        msg = (
            f"[X] *Tarefa falhou*\n\n"
            f"[LISTA] {title[:80]}\n"
            f"[IA] Agente: `{agent}`\n"
            f"[!]️ Erro: `{short_err}`\n"
            f"[HORA] {datetime.now().strftime('%H:%M')}"
        )
        await self.send(msg)

    async def self_improvement(self, patches: int, details: list[str], commit: str = "") -> None:
        """Notifica ciclo de auto-melhoria (se NOTIFY_ON_SELF_IMPROVE=true)."""
        self._daily_stats["improvements"] += patches
        if not self._on_improve or patches == 0:
            return
        lines = [f"[DNA] *Auto-melhoria aplicada!*\n"]
        lines.append(f"• {patches} patch(es) ao código")
        for d in details[:4]:
            lines.append(f"  [OK] {d[:70]}")
        if commit:
            lines.append(f"\n[PACOTE] Commit: `{commit[:8]}`")
        await self.send("\n".join(lines))

    async def system_started(self) -> None:
        """Notifica arranque do sistema."""
        from agents.registry.capabilities import get_registry
        try:
            from agents.capability_registry import get_registry as gr
            reg = gr()
            n_agents = len(reg._data.get("agents", {}))
        except Exception:
            n_agents = "?"
        msg = (
            f"[START] *CORREOTO iniciado!*\n\n"
            f"[IA] {n_agents} agentes prontos\n"
            f"[LOOP] Loop autónomo activo\n"
            f"[DNA] Self-improve a cada 10 ciclos\n"
            f"[HORA] {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"_O ecossistema está a trabalhar. Podes deixar correr._"
        )
        await self.send(msg)

    async def check_daily_summary(self) -> None:
        """
        Verifica se é hora do resumo diário e envia-o.
        Chamado periodicamente pelo loop autónomo.
        """
        if not self._daily:
            return
        now = datetime.now()
        today = date.today()
        if (
            now.hour == self._summary_hour
            and self._last_summary_date != today
        ):
            self._last_summary_date = today
            await self._send_daily_summary()

    async def _send_daily_summary(self) -> None:
        """Envia resumo diário do que o sistema fez."""
        stats = self._daily_stats.copy()

        # Ler memória episódica para dados reais
        try:
            from memory.loop_memory import get_loop_memory
            mem_stats = get_loop_memory().stats()
            total = mem_stats["total_episodes"]
            success_rate = mem_stats["success_rate"]
            by_agent = mem_stats.get("by_agent", {})
            # Top agente do dia
            top = max(by_agent, key=lambda a: by_agent[a]["total"]) if by_agent else "?"
        except Exception:
            total = stats["tasks_done"] + stats["tasks_failed"]
            success_rate = 0
            top = "?"

        # Ler backlog para tarefas pendentes
        pending = 0
        try:
            import json
            from pathlib import Path
            bf = Path("memory/backlog.json")
            if bf.exists():
                tasks = json.loads(bf.read_text(encoding="utf-8"))
                pending = sum(1 for t in tasks if t.get("status") == "pending")
        except Exception:
            pass

        msg = (
            f"[DADOS] *Resumo Diário — {date.today().strftime('%d/%m/%Y')}*\n\n"
            f"[OK] Tarefas concluídas: {stats['tasks_done']}\n"
            f"[X] Tarefas falhadas: {stats['tasks_failed']}\n"
            f"[DNA] Melhorias aplicadas: {stats['improvements']}\n"
            f"[SOBE] Taxa de sucesso: {success_rate}%\n"
            f"⏳ Pendentes: {pending}\n"
            f"[TROF] Agente mais activo: `{top}`\n\n"
            f"_O sistema continuou a trabalhar de forma autónoma._"
        )
        await self.send(msg)
        # Reset diário
        self._daily_stats = {"tasks_done": 0, "tasks_failed": 0, "improvements": 0}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _env_bool(key: str, default: bool) -> bool:
    val = getattr(Config, key, str(default)).lower()
    return val in ("true", "1", "yes")


# ── Singleton global ───────────────────────────────────────────────────────────

_notifier: Optional[Notifier] = None

def get_notifier() -> Notifier:
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier

async def notify(text: str) -> bool:
    """Atalho global: envia notificação ao owner."""
    return await get_notifier().send(text)

def notify_sync(text: str) -> None:
    """Atalho síncrono global."""
    get_notifier().send_sync(text)
