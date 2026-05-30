"""
core/core_protection.py — Protecção do Core do Sistema.

Alguns ficheiros são IMUTÁVEIS — os agentes não os podem alterar
automaticamente. Qualquer tentativa é bloqueada e logada.

Ficheiros protegidos:
  - core/config.py
  - core/core_protection.py (este ficheiro)
  - core/rollback_manager.py
  - main.py (parcialmente — não pode ser apagado)

Sprint 11 do Evolution Roadmap.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROTECTION_DIR = Path("core") / "protection"
HASHES_FILE    = PROTECTION_DIR / "file_hashes.json"
VIOLATIONS_LOG = PROTECTION_DIR / "violations.jsonl"

PROTECTION_DIR.mkdir(parents=True, exist_ok=True)

# Ficheiros absolutamente protegidos — nunca podem ser alterados por agentes
PROTECTED_FILES = {
    "core/config.py",
    "core/core_protection.py",
    "core/rollback_manager.py",
}

# Ficheiros com protecção parcial — podem ser modificados mas não apagados
PARTIALLY_PROTECTED = {
    "main.py",
    "autonomous_loop.py",
    "agents/llm_agent.py",
    "tools/fs_tools.py",
}

# Padrões de código perigoso que não podem estar em nenhum patch
DANGEROUS_PATTERNS = [
    "os.system(",
    "subprocess.call([\"rm\"",
    "shutil.rmtree(",
    "__import__('os').system",
    "eval(",
    "exec(",
    "open('/etc",
    "open('~/.ssh",
]


class CoreProtection:
    """
    Sistema de protecção do core do ecossistema.

    Valida patches antes de aplicar e bloqueia alterações
    não autorizadas a ficheiros críticos.
    """

    def __init__(self):
        self._hashes: dict[str, str] = {}
        self._load_hashes()
        if not self._hashes:
            self._initialise_hashes()

    def is_protected(self, file_path: str) -> bool:
        """Verifica se um ficheiro é protegido."""
        norm = file_path.replace("\\", "/").lstrip("./")
        return (
            norm in PROTECTED_FILES or
            any(norm.endswith(p.lstrip("./")) for p in PROTECTED_FILES)
        )

    def is_partially_protected(self, file_path: str) -> bool:
        """Verifica se um ficheiro tem protecção parcial."""
        norm = file_path.replace("\\", "/").lstrip("./")
        return norm in PARTIALLY_PROTECTED

    def validate_patch(self, patch: dict) -> tuple[bool, str]:
        """
        Valida um patch antes de aplicar.

        Returns:
            (ok, reason) — True se pode aplicar, False com motivo se não pode
        """
        file_path = patch.get("file", "")
        code      = patch.get("code", patch.get("new_code", ""))

        # 1. Ficheiro completamente protegido
        if self.is_protected(file_path):
            self._log_violation(file_path, "tentativa de modificar ficheiro protegido", patch)
            return False, f"❌ BLOQUEADO: '{file_path}' é um ficheiro protegido do core."

        # 2. Verificar padrões perigosos no código
        for pattern in DANGEROUS_PATTERNS:
            if pattern in code:
                self._log_violation(file_path, f"código perigoso: {pattern}", patch)
                return False, f"❌ BLOQUEADO: código contém padrão perigoso '{pattern}'"

        # 3. Verificar integridade de ficheiros parcialmente protegidos
        if self.is_partially_protected(file_path):
            if not self._check_integrity(file_path):
                logger.warning(
                    f"[CoreProtection] ⚠️  {file_path} foi alterado externamente "
                    f"(hash diferente). A actualizar baseline."
                )
                self._update_hash(file_path)

        return True, "ok"

    def check_all_integrity(self) -> dict:
        """
        Verifica integridade de todos os ficheiros protegidos.
        Retorna relatório de qualquer alteração detectada.
        """
        report = {"ok": [], "changed": [], "missing": []}
        for f in list(PROTECTED_FILES) + list(PARTIALLY_PROTECTED):
            path = Path(f)
            if not path.exists():
                report["missing"].append(f)
            elif not self._check_integrity(f):
                report["changed"].append(f)
                self._log_violation(f, "hash diferente detectado na verificação de integridade", {})
            else:
                report["ok"].append(f)
        return report

    def add_to_protected(self, file_path: str, level: str = "partial") -> str:
        """Adiciona um ficheiro à lista de protegidos."""
        if level == "full":
            PROTECTED_FILES.add(file_path)
        else:
            PARTIALLY_PROTECTED.add(file_path)
        self._update_hash(file_path)
        self._save_hashes()
        return f"✅ '{file_path}' adicionado à protecção ({level})."

    def get_violations(self, n: int = 20) -> list[dict]:
        """Retorna os N violations mais recentes."""
        if not VIOLATIONS_LOG.exists():
            return []
        try:
            lines = VIOLATIONS_LOG.read_text(encoding="utf-8").strip().split("\n")
            result = []
            for line in lines[-n:]:
                if line.strip():
                    try:
                        result.append(json.loads(line))
                    except Exception:
                        pass
            return result
        except Exception:
            return []

    def get_summary(self) -> str:
        """Resumo do estado de protecção."""
        integrity = self.check_all_integrity()
        violations = len(self.get_violations())
        lines = [
            f"🔒 **Core Protection**",
            f"Ficheiros protegidos: {len(PROTECTED_FILES)} completos + {len(PARTIALLY_PROTECTED)} parciais",
            f"Integridade: {len(integrity['ok'])}✅ {len(integrity['changed'])}⚠️  {len(integrity['missing'])}❌",
            f"Violations registadas: {violations}",
        ]
        if integrity["changed"]:
            lines.append(f"⚠️  Alterados: {', '.join(integrity['changed'])}")
        return "\n".join(lines)

    def _check_integrity(self, file_path: str) -> bool:
        """Verifica se o hash de um ficheiro é o esperado."""
        expected = self._hashes.get(file_path)
        if expected is None:
            return True  # Sem baseline → considera OK
        current = self._compute_hash(file_path)
        return current == expected

    def _compute_hash(self, file_path: str) -> str:
        try:
            return hashlib.sha256(
                Path(file_path).read_bytes()
            ).hexdigest()[:16]
        except Exception:
            return ""

    def _update_hash(self, file_path: str):
        h = self._compute_hash(file_path)
        if h:
            self._hashes[file_path] = h

    def _initialise_hashes(self):
        """Cria baseline de hashes dos ficheiros actuais."""
        for f in list(PROTECTED_FILES) + list(PARTIALLY_PROTECTED):
            self._update_hash(f)
        self._save_hashes()
        logger.info(f"[CoreProtection] Baseline criado: {len(self._hashes)} ficheiros")

    def _log_violation(self, file_path: str, reason: str, patch: dict):
        from datetime import datetime
        violation = {
            "ts": datetime.now().isoformat(),
            "file": file_path,
            "reason": reason,
            "patch_title": patch.get("title", ""),
        }
        try:
            with open(VIOLATIONS_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(violation, ensure_ascii=False) + "\n")
        except Exception:
            pass
        logger.warning(f"[CoreProtection] 🚨 Violação: {file_path} — {reason}")

    def _load_hashes(self):
        if HASHES_FILE.exists():
            try:
                self._hashes = json.loads(HASHES_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save_hashes(self):
        HASHES_FILE.write_text(
            json.dumps(self._hashes, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


_protection: Optional[CoreProtection] = None

def get_protection() -> CoreProtection:
    global _protection
    if _protection is None:
        _protection = CoreProtection()
    return _protection
