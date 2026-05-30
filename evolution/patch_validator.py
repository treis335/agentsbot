"""
evolution/patch_validator.py — Valida patches antes de aplicar.

Verifica sintaxe, que o search_str existe, e que o resultado é código válido.
Zero API — validação 100% local.
"""

import ast
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class PatchValidator:
    """
    Valida patches antes de os aplicar ao código base.

    Checks:
    1. Ficheiro alvo existe
    2. search_str encontrado no ficheiro (para replace)
    3. Código resultante tem sintaxe válida
    4. Testes básicos não quebram (opcional)
    """

    def __init__(self):
        self.repo_root = Config.REPO_LOCAL_PATH

    def validate(self, patch: dict) -> dict:
        """
        Valida um patch.

        Returns:
            {valid: bool, errors: list[str], warnings: list[str]}
        """
        errors = []
        warnings = []

        patch_type = patch.get("patch_type", "replace")

        # Patches de nota não precisam de validação de código
        if patch_type == "note":
            return {"valid": True, "errors": [], "warnings": ["Patch do tipo 'note' — apenas documentação, não aplica código"]}

        target = patch.get("target_file", "")
        search_str = patch.get("search_str", "")
        replacement = patch.get("replacement", "")

        # Check 1: ficheiro existe
        fpath = self.repo_root / target
        if not fpath.exists():
            errors.append(f"Ficheiro não encontrado: {target}")
            return {"valid": False, "errors": errors, "warnings": warnings}

        content = fpath.read_text(encoding="utf-8")

        # Check 2: search_str existe no ficheiro
        if search_str and search_str not in content:
            errors.append(f"search_str não encontrado em {target}: '{search_str[:60]}'")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check 3: sintaxe do código resultante
        if search_str and replacement is not None:
            new_content = content.replace(search_str, replacement, 1)
        else:
            new_content = content + "\n" + replacement

        if target.endswith(".py"):
            syntax_ok, syntax_err = self._check_syntax(new_content)
            if not syntax_ok:
                errors.append(f"Sintaxe inválida após patch: {syntax_err}")
                return {"valid": False, "errors": errors, "warnings": warnings}

        # Check 4: o replacement não é vazio quando era suposto ter código
        if patch_type == "replace" and not replacement.strip():
            warnings.append("Replacement está vazio — isto irá apagar o código encontrado")

        # Check 5: patch não apaga linhas críticas
        critical_patterns = [
            "def __init__",
            "class Config",
            "import asyncio",
            "async def run",
        ]
        for pattern in critical_patterns:
            if pattern in search_str and pattern not in replacement:
                warnings.append(f"Patch remove definição crítica: '{pattern}'")

        logger.info(f"[PatchValidator] Patch para {target}: {'VÁLIDO' if not errors else 'INVÁLIDO'}")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_syntax(self, code: str) -> tuple[bool, str]:
        """Verifica sintaxe Python."""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def apply(self, patch: dict, dry_run: bool = False) -> dict:
        """
        Aplica um patch validado ao ficheiro alvo.

        Args:
            patch: Patch dict
            dry_run: Se True, simula sem alterar ficheiros

        Returns:
            {success: bool, message: str, backup_path: str}
        """
        patch_type = patch.get("patch_type", "replace")
        target = patch.get("target_file", "")
        search_str = patch.get("search_str", "")
        replacement = patch.get("replacement", "")

        # Notas: apenas log
        if patch_type == "note":
            msg = f"[NOTE] {patch.get('description', '')} -> {target}"
            logger.info(f"[PatchValidator] {msg}")
            return {"success": True, "message": msg, "backup_path": ""}

        fpath = self.repo_root / target
        if not fpath.exists():
            return {"success": False, "message": f"Ficheiro não encontrado: {target}", "backup_path": ""}

        content = fpath.read_text(encoding="utf-8")

        # Criar backup
        backup_path = ""
        if not dry_run:
            backup_dir = Config.MEMORY_DIR / "evolution" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            backup_path = str(backup_dir / f"{target.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
            Path(backup_path).write_text(content, encoding="utf-8")

        # Aplicar patch
        if search_str:
            new_content = content.replace(search_str, replacement, 1)
            if new_content == content:
                return {"success": False, "message": "search_str não encontrado no ficheiro", "backup_path": ""}
        elif patch_type == "append":
            new_content = content + "\n" + replacement
        else:
            return {"success": False, "message": f"patch_type desconhecido: {patch_type}", "backup_path": ""}

        if dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Patch aplicado a {target} ({len(new_content) - len(content):+d} chars)",
                "backup_path": "",
            }

        fpath.write_text(new_content, encoding="utf-8")
        logger.info(f"[PatchValidator] Patch aplicado a {target} (backup: {backup_path})")
        return {
            "success": True,
            "message": f"Patch aplicado a {target}",
            "backup_path": backup_path,
        }

    def rollback(self, backup_path: str, target_file: str) -> bool:
        """Restaura ficheiro a partir do backup."""
        bp = Path(backup_path)
        if not bp.exists():
            logger.error(f"[PatchValidator] Backup não encontrado: {backup_path}")
            return False
        fpath = self.repo_root / target_file
        fpath.write_text(bp.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info(f"[PatchValidator] Rollback: {target_file} restaurado de {backup_path}")
        return True
