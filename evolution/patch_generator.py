"""
evolution/patch_generator.py — Gera patches de código para problemas identificados.

Para propostas simples: gera patches directamente (sem API).
Para propostas complexas: usa DeepSeek para gerar o código.
"""

import ast
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class PatchGenerator:
    """
    Gera patches de código a partir de propostas de melhoria.

    Cada patch é um dict:
    {
        "proposal_id": "...",
        "target_file": "tools/fs_tools.py",
        "patch_type": "insert_before|replace|append",
        "search_str": "string a encontrar no ficheiro",
        "replacement": "novo código",
        "description": "o que o patch faz",
        "generated_by": "local|llm",
        "status": "pending_validation",
    }
    """

    def __init__(self):
        self.patches_dir = Config.MEMORY_DIR / "evolution" / "patches"
        self.patches_dir.mkdir(parents=True, exist_ok=True)
        self.repo_root = Config.REPO_LOCAL_PATH

    def generate(self, proposal: dict, use_llm: bool = True) -> Optional[dict]:
        """
        Gera patch para uma proposta.

        Tenta geração local primeiro; só vai ao LLM se necessário.

        Returns:
            Patch dict, ou None se não foi possível gerar
        """
        action = proposal.get("triggered_by", "")
        complexity = proposal.get("complexity", "medium")
        target_files = proposal.get("target_files", [])

        # Tentativa local para complexidade baixa
        if complexity == "low":
            patch = self._generate_local(proposal)
            if patch:
                self._save_patch(patch)
                return patch

        # LLM para propostas médias/complexas
        if use_llm and target_files:
            patch = self._generate_via_llm(proposal)
            if patch:
                self._save_patch(patch)
                return patch

        logger.warning(f"[PatchGenerator] Não foi possível gerar patch para: {proposal['title']}")
        return None

    def _generate_local(self, proposal: dict) -> Optional[dict]:
        """Gera patches simples sem API, baseado em templates conhecidos."""
        action = proposal.get("triggered_by", "")
        targets = proposal.get("target_files", [])

        # Patch: git pull antes de push
        if action == "fix_git_rejected" and "tools/fs_tools.py" in targets:
            target = self.repo_root / "tools/fs_tools.py"
            if not target.exists():
                return None
            content = target.read_text(encoding="utf-8")
            search = '["git", "commit", "-m", message],'
            if search not in content:
                return None
            return {
                "proposal_id": proposal["id"],
                "target_file": "tools/fs_tools.py",
                "patch_type": "insert_before",
                "search_str": '        ["git", "commit", "-m", message],',
                "replacement": (
                    '        ["git", "pull", "--rebase", "--autostash"],\n'
                    '        ["git", "commit", "-m", message],'
                ),
                "description": "Adicionar git pull --rebase antes do commit para evitar rejeições",
                "generated_by": "local",
                "created_at": datetime.now().isoformat(),
                "status": "pending_validation",
            }

        # Patch: mkdir -p antes de writes
        if action == "fix_file_not_found":
            return {
                "proposal_id": proposal["id"],
                "target_file": "agents/executor.py",
                "patch_type": "note",
                "search_str": "",
                "replacement": "",
                "description": (
                    "NOTA: Adicionar Path(path).parent.mkdir(parents=True, exist_ok=True) "
                    "antes de qualquer open(path, 'w') nos tool handlers"
                ),
                "generated_by": "local",
                "created_at": datetime.now().isoformat(),
                "status": "pending_validation",
            }

        # Patch: clean backlog
        if action == "clean_backlog":
            return {
                "proposal_id": proposal["id"],
                "target_file": "autonomous_loop.py",
                "patch_type": "note",
                "search_str": "",
                "replacement": "",
                "description": (
                    "NOTA: Em mark_task_failed(), se retry_count >= 3, "
                    "mover tarefa para status='archived' em vez de 'failed'"
                ),
                "generated_by": "local",
                "created_at": datetime.now().isoformat(),
                "status": "pending_validation",
            }

        return None

    def _generate_via_llm(self, proposal: dict) -> Optional[dict]:
        """Usa DeepSeek para gerar patch de código."""
        target_file = proposal.get("target_files", [None])[0]
        if not target_file:
            return None

        fpath = self.repo_root / target_file
        if not fpath.exists():
            logger.warning(f"[PatchGenerator] Ficheiro não encontrado: {fpath}")
            return None

        # Ler apenas as primeiras 150 linhas para não gastar tokens
        try:
            lines = fpath.read_text(encoding="utf-8").splitlines()[:150]
            file_excerpt = "\n".join(lines)
        except Exception:
            return None

        try:
            import openai
            client = openai.OpenAI(
                api_key=Config.DEEPSEEK_API_KEY,
                base_url=Config.DEEPSEEK_BASE_URL,
            )

            prompt = f"""Gera um patch Python mínimo para este ficheiro com base na proposta de melhoria.

FICHEIRO ({target_file}, primeiras 150 linhas):
```python
{file_excerpt}
```

PROPOSTA:
- Título: {proposal['title']}
- Descrição: {proposal['description']}
- Hint: {proposal['patch_hint']}

Responde APENAS com JSON válido (sem markdown):
{{
  "search_str": "string exacta a encontrar no ficheiro (5-20 palavras)",
  "replacement": "novo código que substitui search_str",
  "description": "o que o patch faz em 1 frase",
  "patch_type": "replace"
}}

Se não consegues gerar um patch seguro, responde: {{"skip": true, "reason": "motivo"}}"""

            response = client.chat.completions.create(
                model=Config.DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1,
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)

            if data.get("skip"):
                logger.info(f"[PatchGenerator] LLM optou por skip: {data.get('reason')}")
                return None

            return {
                "proposal_id": proposal["id"],
                "target_file": target_file,
                "patch_type": data.get("patch_type", "replace"),
                "search_str": data.get("search_str", ""),
                "replacement": data.get("replacement", ""),
                "description": data.get("description", ""),
                "generated_by": "llm",
                "created_at": datetime.now().isoformat(),
                "status": "pending_validation",
            }

        except Exception as e:
            logger.error(f"[PatchGenerator] Erro LLM: {e}")
            return None

    def _save_patch(self, patch: dict):
        """Persiste patch no disco."""
        date_str = datetime.now().strftime("%Y%m%d")
        fpath = self.patches_dir / f"patches_{date_str}.json"
        existing = []
        if fpath.exists():
            try:
                existing = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing.append(patch)
        fpath.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_pending_patches(self, limit: int = 10) -> list[dict]:
        """Retorna patches aguardando validação."""
        all_patches = []
        for fpath in sorted(self.patches_dir.glob("patches_*.json"), reverse=True)[:7]:
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                all_patches.extend(data)
            except Exception:
                pass
        return [p for p in all_patches if p.get("status") == "pending_validation"][:limit]
