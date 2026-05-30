"""
log_cleanup.py — Limpeza e rotação de logs do ecossistema Correoto
===================================================================
- Remove logs antigos (>7 dias ou >10MB)
- Compacta logs grandes
- Remove erros repetidos (dedup)
- Corre automaticamente ou manualmente

Uso:
    python scripts/log_cleanup.py              # Modo normal
    python scripts/log_cleanup.py --dry-run    # Apenas mostra o que faria
    python scripts/log_cleanup.py --force      # Força limpeza total
"""
import os
import sys
import glob
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent.parent
LOG_DIR = BASE
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_LOG_AGE_DAYS = 7
DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LOG_CLEANUP] %(message)s")
log = logging.getLogger("log_cleanup")

def human_size(n):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def cleanup():
    log.info("=" * 60)
    log.info("LOG CLEANUP — A analisar logs...")
    if DRY_RUN:
        log.info("[DRY RUN] Nenhuma alteração será feita.")
    log.info("=" * 60)

    log_files = []
    # Procurar todos os .log na raiz e subpastas
    for pattern in ["*.log", "*.log.*", "*.txt"]:
        log_files.extend(BASE.glob(pattern))
    for pattern in ["*.log", "*.log.*"]:
        log_files.extend((BASE / "logs").glob(pattern))
    for pattern in ["*.log", "*.log.*"]:
        log_files.extend((BASE / "cerebro").glob(pattern))

    total_saved = 0
    total_removed = 0

    for fpath in sorted(set(log_files)):
        try:
            size = fpath.stat().st_size
            age_days = (datetime.now() - datetime.fromtimestamp(fpath.stat().st_mtime)).days
            action = None

            # Critério 1: Logs muito grandes (>10MB)
            if size > MAX_LOG_SIZE:
                action = f"Tamanho excessivo ({human_size(size)})"

            # Critério 2: Logs muito antigos (>7 dias)
            elif age_days > MAX_LOG_AGE_DAYS:
                action = f"Antigo ({age_dias}d atrás)"

            # Critério 3: Logs vazios
            elif size == 0 and fpath.name not in [".gitkeep"]:
                action = "Vazio"

            if action:
                if DRY_RUN:
                    log.info(f"  🗑️  Remover: {fpath.name} ({human_size(size)}) — {action}")
                else:
                    # Comprimir se for grande, apagar se for pequeno
                    if size > 1024 * 1024:  # >1MB: comprimir
                        gz_path = fpath.with_suffix(fpath.suffix + ".gz")
                        with open(fpath, 'rb') as f_in:
                            with gzip.open(gz_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        os.remove(fpath)
                        log.info(f"  📦 Comprimido: {fpath.name} -> {gz_path.name} ({human_size(size)} -> {human_size(os.path.getsize(gz_path))})")
                        total_saved += size - os.path.getsize(gz_path)
                    else:
                        os.remove(fpath)
                        log.info(f"  🗑️  Removido: {fpath.name} ({human_size(size)})")
                        total_removed += size

        except Exception as e:
            log.warning(f"  ⚠️  Erro ao processar {fpath.name}: {e}")

    # Remover também ficheiros .lock obsoletos (se o processo já não existir)
    for lock_file in BASE.glob("*.lock"):
        try:
            content = lock_file.read_text(encoding="utf-8", errors="replace")
            import json, socket
            pid = None
            try:
                data = json.loads(content)
                pid = data.get("pid")
            except:
                pid = int(content.strip())
            
            if pid:
                # Verificar se o processo existe
                if os.name == "nt":
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.OpenProcess(0x0400, False, pid)
                    if handle:
                        kernel32.CloseHandle(handle)
                        # Processo ativo, manter lock
                        continue
                else:
                    try:
                        os.kill(pid, 0)
                        continue  # Processo ativo
                    except OSError:
                        pass  # Processo morto
            
            # Processo não existe, remover lock
            if not DRY_RUN:
                lock_file.unlink()
                log.info(f"  🔓 Lock removido: {lock_file.name} (PID {pid} já não existe)")
            else:
                log.info(f"  🔓 Removeria lock: {lock_file.name} (PID {pid} já não existe)")
        except Exception as e:
            pass

    log.info("=" * 60)
    if DRY_RUN:
        log.info(f"📊 [DRY RUN] Seriam removidos/compactados {total_removed + total_saved} bytes")
    else:
        log.info(f"📊 Limpeza concluída! Libertados {human_size(total_removed + total_saved)}")
    log.info("=" * 60)

if __name__ == "__main__":
    cleanup()
