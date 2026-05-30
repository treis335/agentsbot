"""
core/bus_replay.py — Replay de eventos não processados ao arrancar.

Ao iniciar o sistema, verifica os logs JSONL do event bus e
re-entrega qualquer evento que não foi processado (ex: crash a meio).

Chamado uma vez no arranque, antes do sistema ficar activo.

Uso (em main.py):
    from core.bus_replay import replay_pending_events
    await replay_pending_events(bus)
"""

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_EVENT_LOG_DIR = Path("memory") / "event_log"


async def replay_pending_events(
    bus,
    log_dir: Optional[Path] = None,
    days_back: int = 2,
    max_events: int = 500,
) -> int:
    """
    Re-entrega eventos não processados dos últimos N dias.

    Args:
        bus: instância de PersistentEventBus (ou compatível)
        log_dir: directório dos logs (default: memory/event_log/)
        days_back: quantos dias atrás verificar (default: 2)
        max_events: limite máximo de eventos a replay (protecção)

    Returns:
        Número de eventos reenviados
    """
    log_dir = log_dir or _EVENT_LOG_DIR
    if not log_dir.exists():
        logger.info("[BusReplay] Sem logs para replay.")
        return 0

    total_replayed = 0
    today = date.today()

    # Verificar os últimos N dias (hoje + dias anteriores)
    for days_ago in range(days_back, -1, -1):
        target_date = today - timedelta(days=days_ago)
        log_path = log_dir / f"{target_date.isoformat()}.jsonl"

        if not log_path.exists():
            continue

        # Saltar o ficheiro de hoje (eventos actuais são tratados normalmente)
        # Excepto se o processo morreu hoje antes de processar
        pending = bus.unprocessed_events(log_path)

        if not pending:
            continue

        # Limitar total
        remaining = max_events - total_replayed
        if remaining <= 0:
            logger.warning(f"[BusReplay] Limite de {max_events} eventos atingido.")
            break

        batch = pending[:remaining]
        logger.info(
            f"[BusReplay] {log_path.name}: {len(pending)} evento(s) pendente(s) "
            f"— replay de {len(batch)}"
        )

        for event in batch:
            try:
                event_type = event.get("type", "unknown")
                logger.debug(f"[BusReplay] Replay: {event_type} [{event.get('id', '?')}]")
                await bus.publish_raw(event)
                total_replayed += 1
            except Exception as e:
                logger.error(f"[BusReplay] Erro ao replay {event.get('id', '?')}: {e}")

    if total_replayed > 0:
        logger.info(f"[BusReplay] [OK] {total_replayed} evento(s) reenviado(s)")
    else:
        logger.info("[BusReplay] Sem eventos pendentes — sistema limpo.")

    return total_replayed


def compact_log(log_path: Path) -> int:
    """
    Compacta um ficheiro de log JSONL:
    Remove entradas de patch e mantém apenas o estado final de cada evento.
    Útil para manter ficheiros de log pequenos.

    Returns:
        Número de linhas removidas.
    """
    import json

    if not log_path.exists():
        return 0

    events: dict[str, dict] = {}
    processed_ids: set[str] = set()
    original_lines = 0

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                original_lines += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if record.get("_patch"):
                    processed_ids.add(record["id"])
                else:
                    events[record["id"]] = record

        # Marcar processed inline nos eventos
        for eid in processed_ids:
            if eid in events:
                events[eid]["processed"] = True

        # Reescrever ficheiro compactado
        with open(log_path, "w", encoding="utf-8") as f:
            for event in events.values():
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

        new_lines = len(events)
        removed = original_lines - new_lines
        logger.info(f"[BusReplay] Compactado {log_path.name}: {original_lines} → {new_lines} linhas (-{removed})")
        return removed

    except Exception as e:
        logger.error(f"[BusReplay] Erro ao compactar {log_path}: {e}")
        return 0


def compact_old_logs(log_dir: Optional[Path] = None, keep_days: int = 7) -> None:
    """
    Compacta ficheiros de log com mais de N dias.
    Chamado periodicamente para manter o directório limpo.
    """
    log_dir = log_dir or _EVENT_LOG_DIR
    if not log_dir.exists():
        return

    cutoff = date.today() - timedelta(days=keep_days)
    for log_file in sorted(log_dir.glob("*.jsonl")):
        try:
            log_date = date.fromisoformat(log_file.stem)
            if log_date < cutoff:
                compact_log(log_file)
        except ValueError:
            pass  # ficheiro com nome não-padrão, ignorar
