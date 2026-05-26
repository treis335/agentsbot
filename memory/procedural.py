"""
memory/procedural.py — Memória de HOW-TO: procedimentos que resultaram.

Regista sequências de acções bem-sucedidas para reutilização.
Zero API — armazenamento e matching local.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class ProceduralMemory:
    """
    Memória procedimental global (partilhada entre agentes).

    Regista procedimentos que funcionaram:
    {
        "id": "proc_20240101_...",
        "name": "criar_modulo_python",
        "description": "Como criar um módulo Python com testes",
        "trigger_keywords": ["criar modulo", "novo ficheiro python"],
        "steps": ["mkdir pasta", "criar __init__.py", "escrever código", "criar test_*.py"],
        "agent": "developer",
        "success_count": 3,
        "last_used": "iso",
        "tags": ["python", "módulo", "testes"],
    }
    """

    def __init__(self):
        self.memory_dir = Config.MEMORY_DIR / "procedural"
        self.memory_file = self.memory_dir / "procedures.json"
        self._procedures: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if not self.memory_file.exists():
            return self._default_procedures()
        try:
            data = json.loads(self.memory_file.read_text(encoding="utf-8"))
            return data if data else self._default_procedures()
        except Exception:
            return self._default_procedures()

    def _default_procedures(self) -> list[dict]:
        """Procedimentos base conhecidos à partida."""
        return [
            {
                "id": "proc_default_001",
                "name": "criar_ficheiro_python",
                "description": "Criar um novo ficheiro Python com estrutura base",
                "trigger_keywords": ["criar ficheiro", "novo modulo", "novo script", "criar modulo"],
                "steps": [
                    "1. Criar directório pai se necessário (mkdir -p)",
                    "2. Escrever código com docstring no topo",
                    "3. Verificar sintaxe: python3 -m py_compile ficheiro.py",
                    "4. Criar __init__.py se for módulo",
                ],
                "agent": "developer",
                "success_count": 1,
                "last_used": datetime.now().isoformat(),
                "tags": ["python", "ficheiro", "módulo"],
            },
            {
                "id": "proc_default_002",
                "name": "corrigir_bug",
                "description": "Processo de debugging e correção de bug",
                "trigger_keywords": ["corrigir bug", "fix error", "resolver erro", "hotfix"],
                "steps": [
                    "1. Ler o traceback completo para identificar linha e ficheiro",
                    "2. Reproduzir o erro localmente",
                    "3. Identificar a causa raiz (não apenas o sintoma)",
                    "4. Aplicar patch mínimo",
                    "5. Verificar que não quebrou outros módulos",
                    "6. Commit com mensagem descritiva",
                ],
                "agent": "auto_fixer",
                "success_count": 1,
                "last_used": datetime.now().isoformat(),
                "tags": ["bug", "fix", "debugging"],
            },
            {
                "id": "proc_default_003",
                "name": "commit_e_push",
                "description": "Git commit e push correcto",
                "trigger_keywords": ["commit", "push", "guardar alterações", "subir codigo"],
                "steps": [
                    "1. git status para ver ficheiros alterados",
                    "2. git add -A ou ficheiros específicos",
                    "3. git commit -m 'tipo(escopo): descrição clara'",
                    "4. git push origin branch",
                    "5. Verificar output do push — se rejected, fazer git pull primeiro",
                ],
                "agent": "developer",
                "success_count": 1,
                "last_used": datetime.now().isoformat(),
                "tags": ["git", "commit", "push"],
            },
            {
                "id": "proc_default_004",
                "name": "criar_testes",
                "description": "Criar testes unitários para um módulo",
                "trigger_keywords": ["criar testes", "testes unitarios", "pytest", "test coverage"],
                "steps": [
                    "1. Criar tests/test_<modulo>.py",
                    "2. Importar o módulo a testar",
                    "3. Criar classe TestX(unittest.TestCase) ou usar pytest directo",
                    "4. Testar casos normais + edge cases + erros esperados",
                    "5. Correr: python3 -m pytest tests/ -v",
                ],
                "agent": "qa_tester",
                "success_count": 1,
                "last_used": datetime.now().isoformat(),
                "tags": ["testes", "pytest", "qa"],
            },
        ]

    def _save(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(
            json.dumps(self._procedures, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def record_procedure(
        self,
        name: str,
        description: str,
        steps: list[str],
        agent: str,
        trigger_keywords: list[str] = None,
        tags: list[str] = None,
    ) -> str:
        """Regista um novo procedimento bem-sucedido."""
        # Verificar se já existe (actualizar success_count)
        for proc in self._procedures:
            if proc["name"] == name:
                proc["success_count"] = proc.get("success_count", 0) + 1
                proc["last_used"] = datetime.now().isoformat()
                self._save()
                return proc["id"]

        proc_id = f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        entry = {
            "id": proc_id,
            "name": name,
            "description": description,
            "trigger_keywords": trigger_keywords or [],
            "steps": steps,
            "agent": agent,
            "success_count": 1,
            "last_used": datetime.now().isoformat(),
            "tags": tags or [],
        }
        self._procedures.append(entry)
        self._save()
        logger.info(f"[ProceduralMemory] Novo procedimento: {name}")
        return proc_id

    def get_relevant(self, task: str, limit: int = 2) -> list[dict]:
        """
        Retorna procedimentos relevantes para a tarefa.

        Matching por keywords no trigger_keywords e tags.
        """
        task_lower = task.lower()
        scored = []

        for proc in self._procedures:
            score = 0
            for kw in proc.get("trigger_keywords", []):
                if kw.lower() in task_lower:
                    score += 3
            for tag in proc.get("tags", []):
                if tag.lower() in task_lower:
                    score += 1
            # Bónus por uso frequente
            score += min(proc.get("success_count", 0) * 0.5, 2)
            if score > 0:
                scored.append((score, proc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def format_for_prompt(self, procedures: list[dict]) -> str:
        """Formata procedimentos para injeção no system prompt."""
        if not procedures:
            return ""
        lines = ["### Procedimentos Conhecidos (HOW-TO)\n"]
        for proc in procedures:
            lines.append(f"**{proc['name']}**: {proc['description']}")
            for step in proc.get("steps", []):
                lines.append(f"  {step}")
            lines.append("")
        return "\n".join(lines)

    def increment_usage(self, proc_id: str):
        """Incrementa contador de uso de um procedimento."""
        for proc in self._procedures:
            if proc["id"] == proc_id:
                proc["success_count"] = proc.get("success_count", 0) + 1
                proc["last_used"] = datetime.now().isoformat()
                self._save()
                return
