"""
memory/semantica.py — Memoria semantica (conhecimento estruturado).

Armazena conhecimento factual e relacional sobre:
- O projeto (estrutura, modulos, dependencias)
- As ferramentas (como usar cada uma)
- Os agentes (capacidades, personalidades)
- Padroes e convencoes do codigo
- Decisoes arquiteturais

Diferenca da memoria global: aqui o conhecimento e estruturado
em topicos com relacoes entre si.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class SemanticMemory:
    """
    Memoria semantica — conhecimento estruturado do ecossistema.

    Estrutura:
    {
        "project": {
            "name": "Correoto",
            "version": "2.0",
            "structure": {...},
            "dependencies": [...],
        },
        "tools": {
            "write_file": {
                "description": "Escreve conteudo num ficheiro",
                "args": ["path", "content"],
                "examples": [...],
            },
            ...
        },
        "agents": {
            "agent_id": {
                "name": "...",
                "capabilities": [...],
                "soul_summary": "...",
            },
            ...
        },
        "patterns": {
            "naming": "...",
            "structure": "...",
            "conventions": [...],
        },
        "decisions": [
            {
                "date": "...",
                "decision": "...",
                "rationale": "...",
            }
        ]
    }
    """

    def __init__(self):
        self.config = Config
        self.memory_file = self.config.MEMORY_DIR / "semantica" / "knowledge.json"
        self._data: dict = self._load()

    def _load(self) -> dict:
        if not self.memory_file.exists():
            return self._default()
        try:
            return json.loads(self.memory_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[SemanticMemory] Erro ao carregar: {e}")
            return self._default()

    def _save(self) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _default(self) -> dict:
        return {
            "project": {
                "name": "Correoto",
                "version": "2.0",
                "description": "Ecossistema autonomo de agentes IA",
                "structure": {},
                "dependencies": [],
            },
            "tools": {},
            "agents": {},
            "patterns": {
                "naming_conventions": "snake_case para ficheiros Python, PascalCase para classes",
                "code_style": "PEP 8, type hints obrigatorios",
                "commit_style": "conventional commits (feat:, fix:, docs:, refactor:)",
            },
            "decisions": [],
        }

    # --- Projecto ---

    def update_project_info(self, key: str, value: any) -> None:
        """Atualiza informacao sobre o projecto."""
        self._data["project"][key] = value
        self._save()

    def get_project_info(self) -> dict:
        """Retorna informacao do projecto."""
        return self._data["project"]

    # --- Ferramentas ---

    def register_tool(self, name: str, description: str, args: list[str],
                      examples: list[str] | None = None) -> None:
        """Regista uma ferramenta no conhecimento semantico."""
        self._data["tools"][name] = {
            "description": description,
            "args": args,
            "examples": examples or [],
            "updated_at": datetime.now().isoformat(),
        }
        self._save()

    def get_tool_info(self, name: str) -> Optional[dict]:
        """Obtem informacao sobre uma ferramenta."""
        return self._data["tools"].get(name)

    def get_all_tools(self) -> dict:
        """Retorna todas as ferramentas registadas."""
        return self._data["tools"]

    # --- Agentes ---

    def register_agent_knowledge(self, agent_id: str, name: str,
                                  capabilities: list[str],
                                  soul_summary: str = "") -> None:
        """Regista conhecimento sobre um agente."""
        self._data["agents"][agent_id] = {
            "name": name,
            "capabilities": capabilities,
            "soul_summary": soul_summary,
            "updated_at": datetime.now().isoformat(),
        }
        self._save()

    def get_agent_knowledge(self, agent_id: str) -> Optional[dict]:
        """Obtem conhecimento sobre um agente."""
        return self._data["agents"].get(agent_id)

    # --- Decisoes Arquiteturais ---

    def add_decision(self, decision: str, rationale: str) -> None:
        """Regista uma decisao arquitetural."""
        self._data["decisions"].append({
            "date": datetime.now().isoformat(),
            "decision": decision,
            "rationale": rationale,
        })
        self._save()

    def get_decisions(self, limit: int = 20) -> list[dict]:
        """Retorna decisoes arquiteturais."""
        return self._data["decisions"][-limit:]

    # --- Padroes ---

    def update_pattern(self, key: str, value: any) -> None:
        """Atualiza um padrao/convencao."""
        self._data["patterns"][key] = value
        self._save()

    def get_patterns(self) -> dict:
        """Retorna todos os padroes."""
        return self._data["patterns"]

    # --- Util ---

    def get_all(self) -> dict:
        """Retorna todo o conhecimento semantico."""
        return self._data

    def clear(self) -> None:
        """Limpa memoria semantica."""
        self._data = self._default()
        self._save()
