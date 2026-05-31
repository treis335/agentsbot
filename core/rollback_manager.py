"""
core/rollback_manager.py — Sistema de Rollback Automático.

Toda promoção de patch cria um git tag + backup snapshot.
Se o sistema detectar degradação (mais erros, crashes), faz rollback automático.

Sprint 10 do Evolution Roadmap.
"""
import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ROLLBACK_DIR  = Path("core") / "rollback"
SNAPSHOTS_DIR = ROLLBACK_DIR / "snapshots"
ROLLBACK_LOG  = ROLLBACK_DIR / "rollback_history.jsonl"

ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(exist_ok=True)


@dataclass
class Snapshot:
    id: str
    tag: str
    description: str
    files: list            # lista de ficheiros incluídos no snapshot
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    git_commit: str = ""
    error_rate_at_creation: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RollbackEvent:
    snapshot_id: str
    reason: str
    trigger: str           # auto | manual
    success: bool
    files_restored: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class RollbackManager:
    """
    Gere snapshots e rollbacks automáticos.

    Uso:
        manager = get_rollback_manager()
        snap_id = manager.create_snapshot("antes de aplicar patch X", files=["agents/executor.py"])
        # ... aplica patch ...
        if something_broke:
            manager.rollback(snap_id, reason="Aumentaram os erros", trigger="auto")
    """

    # Se a taxa de erro subir mais que este valor após um patch → rollback automático
    ERROR_RATE_THRESHOLD = 0.30  # 30%

    def __init__(self):
        self._snapshots: list[Snapshot] = []
        self._events: list[RollbackEvent] = []
        self._load()

    def create_snapshot(self, description: str,
                        files: Optional[list] = None,
                        error_rate: float = 0.0) -> str:
        """
        Cria snapshot dos ficheiros actuais.
        Retorna o snapshot_id para usar no rollback.
        """
        snap_id = f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        snap_dir = SNAPSHOTS_DIR / snap_id
        snap_dir.mkdir(exist_ok=True)

        # Ficheiros a guardar — por defeito os críticos
        if files is None:
            files = self._get_critical_files()

        saved_files = []
        for rel_path in files:
            src = Path(rel_path)
            if src.exists():
                dest = snap_dir / src.name
                shutil.copy2(src, dest)
                saved_files.append(rel_path)

        # Git tag
        git_commit = self._get_git_commit()
        try:
            subprocess.run(
                ["git", "tag", snap_id],
                capture_output=True, timeout=10
            )
        except Exception:
            pass

        snap = Snapshot(
            id=snap_id,
            tag=snap_id,
            description=description,
            files=saved_files,
            git_commit=git_commit,
            error_rate_at_creation=error_rate,
        )
        self._snapshots.append(snap)
        self._save_snapshots()

        logger.info(f"[Rollback] 📸 Snapshot: {snap_id} — {description} ({len(saved_files)} ficheiros)")
        return snap_id

    def rollback(self, snapshot_id: str, reason: str,
                 trigger: str = "manual") -> bool:
        """
        Restaura o estado de um snapshot.

        Returns:
            True se rollback bem-sucedido, False se falhou.
        """
        snap = self._find_snapshot(snapshot_id)
        if not snap:
            logger.error(f"[Rollback] Snapshot {snapshot_id} não encontrado.")
            return False

        snap_dir = SNAPSHOTS_DIR / snap.id
        if not snap_dir.exists():
            logger.error(f"[Rollback] Directório de snapshot não existe: {snap_dir}")
            return False

        files_restored = 0
        try:
            for rel_path in snap.files:
                src  = snap_dir / Path(rel_path).name
                dest = Path(rel_path)
                if src.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    files_restored += 1

            # Tentar reverter via git se temos o commit
            if snap.git_commit:
                try:
                    subprocess.run(
                        ["git", "checkout", snap.git_commit, "--"] + snap.files,
                        capture_output=True, timeout=30
                    )
                except Exception:
                    pass  # Continua mesmo se git falhar

            event = RollbackEvent(
                snapshot_id=snapshot_id,
                reason=reason,
                trigger=trigger,
                success=True,
                files_restored=files_restored,
            )
            self._events.append(event)
            self._save_events()

            from core.event_logger import log_rollback
            log_rollback(snap.description, reason)

            logger.info(
                f"[Rollback] ⏪ Rollback OK: {snapshot_id} "
                f"({files_restored} ficheiros) | {reason}"
            )
            return True

        except Exception as e:
            event = RollbackEvent(
                snapshot_id=snapshot_id,
                reason=reason,
                trigger=trigger,
                success=False,
            )
            self._events.append(event)
            self._save_events()
            logger.error(f"[Rollback] Falhou: {e}")
            return False

    def check_and_auto_rollback(self, current_error_rate: float,
                                last_snapshot_id: str) -> bool:
        """
        Verifica se a taxa de erro aumentou muito desde o último snapshot.
        Se sim, faz rollback automático.

        Returns:
            True se rollback foi feito, False se não foi necessário.
        """
        snap = self._find_snapshot(last_snapshot_id)
        if not snap:
            return False

        baseline = snap.error_rate_at_creation
        increase = current_error_rate - baseline

        if increase > self.ERROR_RATE_THRESHOLD:
            logger.warning(
                f"[Rollback] ⚠️  Taxa de erro subiu {increase:.0%} "
                f"({baseline:.0%} → {current_error_rate:.0%}) — a fazer rollback automático"
            )
            self.rollback(
                last_snapshot_id,
                reason=f"Taxa de erro subiu {increase:.0%} acima do baseline",
                trigger="auto",
            )
            return True

        return False

    def get_latest_snapshot(self) -> Optional[Snapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def list_snapshots(self, n: int = 10) -> list[Snapshot]:
        return self._snapshots[-n:]

    def get_stats(self) -> dict:
        total_rollbacks = len(self._events)
        auto_rollbacks  = sum(1 for e in self._events if e.trigger == "auto")
        return {
            "snapshots":      len(self._snapshots),
            "rollbacks":      total_rollbacks,
            "auto_rollbacks": auto_rollbacks,
            "last_snapshot":  self._snapshots[-1].id if self._snapshots else None,
        }

    def _get_critical_files(self) -> list[str]:
        """Ficheiros críticos que sempre fazem parte do snapshot."""
        critical = [
            "main.py",
            "autonomous_loop.py",
            "agents/llm_agent.py",
            "agents/executor.py",
            "core/config.py",
            "tools/fs_tools.py",
        ]
        return [f for f in critical if Path(f).exists()]

    def _get_git_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _find_snapshot(self, snap_id: str) -> Optional[Snapshot]:
        for s in reversed(self._snapshots):
            if s.id == snap_id:
                return s
        return None

    def _load(self):
        index = ROLLBACK_DIR / "snapshots.json"
        if index.exists():
            try:
                data = json.loads(index.read_text(encoding="utf-8"))
                self._snapshots = [
                    Snapshot(**{k: v for k, v in d.items()
                                if k in Snapshot.__dataclass_fields__})
                    for d in data
                ]
            except Exception:
                pass
        if ROLLBACK_LOG.exists():
            try:
                for line in ROLLBACK_LOG.read_text(encoding="utf-8").strip().split("\n"):
                    if line.strip():
                        d = json.loads(line)
                        self._events.append(RollbackEvent(
                            **{k: v for k, v in d.items()
                               if k in RollbackEvent.__dataclass_fields__}
                        ))
            except Exception:
                pass

    def _save_snapshots(self):
        (ROLLBACK_DIR / "snapshots.json").write_text(
            json.dumps([s.to_dict() for s in self._snapshots],
                       indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _save_events(self):
        try:
            with open(ROLLBACK_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(self._events[-1].to_dict(),
                                   ensure_ascii=False) + "\n")
        except Exception:
            pass


_manager: Optional[RollbackManager] = None

def get_rollback_manager() -> RollbackManager:
    global _manager
    if _manager is None:
        _manager = RollbackManager()
    return _manager
