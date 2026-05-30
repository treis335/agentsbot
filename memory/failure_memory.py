"""
memory/failure_memory.py — Registo estruturado de falhas com causa + solução.

Separa as falhas da memória episódica geral para consulta rápida.
Zero API — armazenamento e matching puramente local.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class FailureMemory:
    """
    Registo estruturado de falhas por agente.

    Cada entrada:
    {
        "id": "uuid-like",
        "timestamp": "iso",
        "agent": "developer",
        "task_snippet": "primeiros 120 chars da tarefa",
        "action": "write_file",
        "error_type": "PermissionError",  # categoria normalizada
        "error_detail": "texto do erro",
        "cause": "causa inferida",
        "solution": "o que resolveu (ou None se não resolvido)",
        "resolved": True/False,
        "retry_count": 1,
    }
    """

    # Padrões para categorizar erros automaticamente
    ERROR_PATTERNS = [
        (r"PermissionError|permission denied", "permission_error"),
        (r"FileNotFoundError|No such file", "file_not_found"),
        (r"SyntaxError|IndentationError", "syntax_error"),
        (r"ImportError|ModuleNotFoundError", "import_error"),
        (r"TimeoutError|timed out", "timeout"),
        (r"ConnectionError|Connection refused", "connection_error"),
        (r"JSONDecodeError|json.decoder", "json_error"),
        (r"git.*rejected|remote.*rejected", "git_rejected"),
        (r"Traceback|Exception|Error:", "generic_error"),
    ]

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memory_dir = Config.MEMORY_DIR / "failures"
        self.memory_file = self.memory_dir / f"{agent_id}.json"
        self._failures: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if not self.memory_file.exists():
            return []
        try:
            return json.loads(self.memory_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        # Manter últimas 200 falhas
        data = self._failures[-200:]
        self.memory_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _classify_error(self, error_text: str) -> str:
        """Classifica o tipo de erro por regex."""
        for pattern, category in self.ERROR_PATTERNS:
            if re.search(pattern, error_text, re.IGNORECASE):
                return category
        return "unknown_error"

    def _infer_cause(self, error_type: str, error_detail: str, action: str) -> str:
        """Infere causa provável do erro (heurísticas locais)."""
        causes = {
            "permission_error": "Ficheiro ou directório sem permissões de escrita/leitura",
            "file_not_found": f"Caminho n?o existe: verificar paths em '{action}'",
            "syntax_error": "Erro de sintaxe Python no código gerado",
            "import_error": "Módulo não instalado ou caminho errado",
            "timeout": "Operação demorou demasiado — timeout configurado demasiado curto",
            "connection_error": "Servidor inacessível ou URL incorrecta",
            "json_error": "JSON malformado — verificar output da tool",
            "git_rejected": "Push rejeitado — branch protegida ou conflito",
            "generic_error": "Erro genérico — ver error_detail para diagnóstico",
            "unknown_error": "Causa desconhecida — analisar manualmente",
        }
        return causes.get(error_type, "Causa desconhecida")

    def record_failure(
        self,
        action: str,
        error_text: str,
        task_snippet: str = "",
        retry_count: int = 0,
    ) -> str:
        """
        Regista uma falha estruturada.

        Returns:
            ID da entrada criada
        """
        error_type = self._classify_error(error_text)
        cause = self._infer_cause(error_type, error_text, action)
        entry_id = f"{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id,
            "task_snippet": task_snippet[:120],
            "action": action,
            "error_type": error_type,
            "error_detail": error_text[:300],
            "cause": cause,
            "solution": None,
            "resolved": False,
            "retry_count": retry_count,
        }

        self._failures.append(entry)
        self._save()
        logger.debug(f"[FailureMemory:{self.agent_id}] Falha registada: {error_type} em {action}")
        return entry_id

    def mark_resolved(self, entry_id: str, solution: str):
        """Marca uma falha como resolvida com a solução encontrada."""
        for entry in self._failures:
            if entry["id"] == entry_id:
                entry["resolved"] = True
                entry["solution"] = solution[:200]
                self._save()
                return

    def get_similar_failures(self, task: str, action: str = "", limit: int = 3) -> list[dict]:
        """
        Retorna falhas semelhantes à tarefa atual.

        Matching por: action igual + palavras comuns no task_snippet.
        """
        task_words = set(task.lower().split())
        scored = []

        for f in self._failures:
            score = 0
            # Match por action
            if action and f.get("action") == action:
                score += 3
            # Match por palavras no task_snippet
            snippet_words = set(f.get("task_snippet", "").lower().split())
            common = task_words & snippet_words
            score += len(common)
            if score > 0:
                scored.append((score, f))

        # Ordenar por score desc, timestamp desc
        scored.sort(key=lambda x: (x[0], x[1]["timestamp"]), reverse=True)
        return [f for _, f in scored[:limit]]

    def get_unresolved(self, limit: int = 5) -> list[dict]:
        """Retorna falhas não resolvidas mais recentes."""
        unresolved = [f for f in self._failures if not f["resolved"]]
        return unresolved[-limit:]

    def get_by_error_type(self, error_type: str, limit: int = 5) -> list[dict]:
        """Retorna falhas de um tipo específico."""
        matches = [f for f in self._failures if f["error_type"] == error_type]
        return matches[-limit:]

    def format_for_prompt(self, failures: list[dict]) -> str:
        """Formata falhas para injeção no system prompt."""
        if not failures:
            return ""
        lines = ["### Falhas Similares (aprende com estes erros)\n"]
        for f in failures:
            resolved_marker = "[OK] Resolvido" if f["resolved"] else "[X] Não resolvido"
            lines.append(f"- [{f['error_type']}] em `{f['action']}`: {f['cause']}")
            if f["solution"]:
                lines.append(f"  Solu??o: {f['solution']}")
            lines.append(f"  ({resolved_marker}, {f['timestamp'][:10]})")
        return "\n".join(lines)

    def stats(self) -> dict:
        """Estatísticas das falhas."""
        total = len(self._failures)
        resolved = sum(1 for f in self._failures if f["resolved"])
        by_type: dict[str, int] = {}
        for f in self._failures:
            et = f["error_type"]
            by_type[et] = by_type.get(et, 0) + 1
        return {
            "total": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "resolution_rate": resolved / total if total else 0.0,
            "by_error_type": by_type,
        }
