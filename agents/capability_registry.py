"""
agents/capability_registry.py — Registo de capabilities por agente.

Carrega capabilities.json e faz match task->agente por scoring local.
Zero chamadas API — decisão puramente local.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Caminho para o ficheiro de capabilities
CAPABILITIES_PATH = Path(__file__).parent / "registry" / "capabilities.json"


class CapabilityRegistry:
    """
    Registo central de capabilities dos agentes.

    Uso:
        registry = CapabilityRegistry()
        best_agent = registry.match(task_description, available_agents)
        score_map = registry.score_all(task_description)
    """

    def __init__(self, capabilities_path: Optional[Path] = None):
        self._path = capabilities_path or CAPABILITIES_PATH
        self._data: dict = {}
        self._load()

    def _load(self):
        """Carrega capabilities do ficheiro JSON."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            agents = self._data.get("agents", {})
            logger.info(f"[CapabilityRegistry] Carregado: {len(agents)} agentes registados")
        except FileNotFoundError:
            logger.warning(f"[CapabilityRegistry] {self._path} não encontrado — usando defaults")
            self._data = {"agents": {}}
        except json.JSONDecodeError as e:
            logger.error(f"[CapabilityRegistry] Erro JSON: {e}")
            self._data = {"agents": {}}

    def reload(self):
        """Recarrega capabilities (útil após auto-registo)."""
        self._load()

    def score_all(self, task: str, success_history: Optional[dict] = None) -> dict[str, float]:
        """
        Calcula score de compatibilidade de cada agente com a tarefa.

        Args:
            task: Descrição da tarefa
            success_history: {agent_name: success_rate (0.0-1.0)} da memória episódica

        Returns:
            {agent_name: score} — score maior = melhor match
        """
        task_lower = task.lower()
        agents = self._data.get("agents", {})
        scores: dict[str, float] = {}

        for agent_name, config in agents.items():
            score = float(config.get("base_score", 0))

            # Score por keywords (peso 2 por keyword encontrada)
            keywords = config.get("keywords", [])
            keyword_hits = sum(
                2 for kw in keywords
                if kw.lower() in task_lower
            )
            score += keyword_hits

            # Score por task_types (peso 3 — match mais específico)
            task_types = config.get("task_types", [])
            type_hits = sum(
                3 for tt in task_types
                if tt.lower().replace("_", " ") in task_lower
                or tt.lower() in task_lower
            )
            score += type_hits

            # Bónus por histórico de sucesso (peso 0-5)
            if success_history:
                history_key = config.get("success_history_key", agent_name)
                rate = success_history.get(history_key, 0.5)
                score += rate * 5

            scores[agent_name] = score

        return scores

    def match(
        self,
        task: str,
        available_agents: Optional[list[str]] = None,
        success_history: Optional[dict] = None,
        fallback: str = "supervisor",
    ) -> str:
        """
        Retorna o melhor agente para a tarefa.

        Args:
            task: Descrição da tarefa
            available_agents: Lista de agentes disponíveis (None = todos)
            success_history: Taxas de sucesso da memória episódica
            fallback: Agente a usar se nenhum match

        Returns:
            Nome do agente com maior score
        """
        scores = self.score_all(task, success_history)

        # Filtrar por agentes disponíveis
        if available_agents:
            scores = {k: v for k, v in scores.items() if k in available_agents}

        if not scores:
            logger.warning(f"[CapabilityRegistry] Nenhum agente disponível — fallback: {fallback}")
            return fallback

        # Escolher o agente com maior score
        best_agent = max(scores, key=lambda k: scores[k])
        best_score = scores[best_agent]

        # Log de decisão
        top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_str = ", ".join(f"{a}={s:.1f}" for a, s in top3)
        logger.info(f"[CapabilityRegistry] Match para '{task[:60]}...': {best_agent} (top3: {top3_str})")

        # Se o melhor score for 0 ou negativo, usar fallback
        if best_score <= 0:
            logger.info(f"[CapabilityRegistry] Score insuficiente ({best_score}) — fallback: {fallback}")
            return fallback

        return best_agent

    def get_agent_skills(self, agent_name: str) -> list[str]:
        """Retorna lista de skills de um agente."""
        agents = self._data.get("agents", {})
        return agents.get(agent_name, {}).get("skills", [])

    def get_agent_description(self, agent_name: str) -> str:
        """Retorna descrição de um agente."""
        agents = self._data.get("agents", {})
        return agents.get(agent_name, {}).get("description", "Agente desconhecido")

    def list_agents(self) -> list[str]:
        """Lista todos os agentes registados."""
        return list(self._data.get("agents", {}).keys())

    def register_skill(self, agent_name: str, skill: str, keywords: list[str] = None):
        """
        Regista uma nova skill para um agente em runtime.
        Persiste no ficheiro JSON.

        Args:
            agent_name: Nome do agente
            skill: Nome da skill
            keywords: Keywords associadas
        """
        agents = self._data.setdefault("agents", {})
        if agent_name not in agents:
            agents[agent_name] = {
                "description": f"Agente {agent_name}",
                "skills": [],
                "keywords": [],
                "task_types": [],
                "base_score": 0,
                "success_history_key": agent_name
            }

        agent_config = agents[agent_name]

        # Adicionar skill se não existir
        if skill not in agent_config.get("skills", []):
            agent_config.setdefault("skills", []).append(skill)

        # Adicionar keywords novas
        if keywords:
            existing_kws = agent_config.setdefault("keywords", [])
            for kw in keywords:
                if kw not in existing_kws:
                    existing_kws.append(kw)

        # Persistir
        self._save()
        logger.info(f"[CapabilityRegistry] Registada skill '{skill}' para '{agent_name}'")

    def _save(self):
        """Persiste capabilities no ficheiro JSON."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[CapabilityRegistry] Erro ao guardar: {e}")


# Instância global (singleton lazy)
_registry: Optional[CapabilityRegistry] = None


def get_registry() -> CapabilityRegistry:
    """Retorna instância global do registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry
