"""
agents/reflection_engine.py — Reflection Engine completo.

Após cada tarefa:
1. Analisa o que correu bem/mal (heurísticas locais, zero API)
2. Para casos complexos, usa 1 chamada LLM
3. Detecta padrões repetidos (Pattern Discovery)
4. Sugere/cria nova skill quando padrão se repete 3x
5. Guarda reflexões classificadas por tipo

Sprint 2 do Evolution Roadmap.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_REFLECTIONS_FILE  = Path("memory") / "reflections.json"
_PATTERNS_FILE     = Path("memory") / "global" / "patterns.json"
_MAX_REFLECTIONS   = 500
_PATTERN_THRESHOLD = 3   # vezes que um padrão deve repetir para gerar skill


@dataclass
class Reflection:
    task_id:            str
    task_desc:          str
    agent:              str
    success:            bool
    timestamp:          str = field(default_factory=lambda: datetime.now().isoformat())
    what_worked:        str = ""
    what_failed:        str = ""
    adjusted_strategy:  str = ""
    new_skill_triggered: bool = False
    new_skill_name:     str = ""
    raw_result:         str = ""
    pattern_id:         str = ""     # id do padrão detectado (se houver)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt_context(self) -> str:
        icon = "✅" if self.success else "❌"
        lines = [f"{icon} Reflexão de tarefa similar ({self.timestamp[:10]}):"]
        if self.what_worked:
            lines.append(f"  • Funcionou: {self.what_worked}")
        if self.what_failed:
            lines.append(f"  • Falhou: {self.what_failed}")