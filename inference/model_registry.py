"""
inference/model_registry.py — Registo de modelos disponíveis.

Mantém a lista de modelos Ollama + DeepSeek, com metadados
sobre cada um (uso recomendado, limite de tokens, custo relativo).

Atualizado automaticamente ao arrancar via sync_local_models().
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    OLLAMA  = "ollama"
    DEEPSEEK = "deepseek"


@dataclass
class ModelInfo:
    name: str
    provider: ModelProvider
    context_window: int = 8192
    max_output_tokens: int = 2000
    cost_per_1k_tokens: float = 0.0    # USD; 0.0 = gratuito (local)
    recommended_for: list[str] = field(default_factory=list)
    available: bool = True              # atualizado dinamicamente


# --- CATÁLOGO ESTÁTICO ---------------------------------------------------------
# Ollama — gratuito, local
# DeepSeek — pago, cloud

MODEL_CATALOG: dict[str, ModelInfo] = {
    # -- Ollama ------------------------------------------------------------------
    "qwen2.5-coder:7b": ModelInfo(
        name="qwen2.5-coder:7b",
        provider=ModelProvider.OLLAMA,
        context_window=32768,
        max_output_tokens=4096,
        cost_per_1k_tokens=0.0,
        recommended_for=["code", "fix", "syntax", "review", "docstring"],
    ),
    "qwen2.5-coder:14b": ModelInfo(
        name="qwen2.5-coder:14b",
        provider=ModelProvider.OLLAMA,
        context_window=32768,
        max_output_tokens=4096,
        cost_per_1k_tokens=0.0,
        recommended_for=["code", "refactor", "architecture"],
    ),
    "llama3.2:3b": ModelInfo(
        name="llama3.2:3b",
        provider=ModelProvider.OLLAMA,
        context_window=8192,
        max_output_tokens=2048,
        cost_per_1k_tokens=0.0,
        recommended_for=["classify", "summarize", "simple_text", "routing"],
    ),
    "mistral:7b": ModelInfo(
        name="mistral:7b",
        provider=ModelProvider.OLLAMA,
        context_window=8192,
        max_output_tokens=2048,
        cost_per_1k_tokens=0.0,
        recommended_for=["general", "reasoning", "analysis"],
    ),
    # -- DeepSeek (cloud) --------------------------------------------------------
    "deepseek-chat": ModelInfo(
        name="deepseek-chat",
        provider=ModelProvider.DEEPSEEK,
        context_window=65536,
        max_output_tokens=8192,
        cost_per_1k_tokens=0.00027,   # ~$0.27/M tokens (input, DeepSeek V3)
        recommended_for=["complex", "creative", "multi_file", "architecture"],
    ),
    "deepseek-reasoner": ModelInfo(
        name="deepseek-reasoner",
        provider=ModelProvider.DEEPSEEK,
        context_window=65536,
        max_output_tokens=8192,
        cost_per_1k_tokens=0.00055,
        recommended_for=["math", "logic", "step_by_step"],
    ),
}


class ModelRegistry:
    """
    Registo central de modelos.
    Sincroniza disponibilidade com o Ollama ao arrancar.
    """

    def __init__(self):
        self._models = dict(MODEL_CATALOG)  # cópia local

    async def sync_local_models(self, ollama_url: str = "http://localhost:11434") -> list[str]:
        """
        Sincroniza disponibilidade de modelos Ollama.
        Marca como available=False os que não existem localmente.
        Retorna lista de modelos disponíveis.
        """
        try:
            from inference.local_client import OllamaClient
            from core.config import Config as _Cfg
            local_model = getattr(_Cfg, "LOCAL_MODEL", "qwen2.5-coder:7b")
            client = OllamaClient(base_url=ollama_url, model=local_model)
            available = await client.list_models()

            # Normalizar nomes (Ollama pode retornar "qwen2.5-coder:7b" ou variações)
            available_set = {m.lower() for m in available}

            for name, info in self._models.items():
                if info.provider == ModelProvider.OLLAMA:
                    # Match exacto ou prefixo
                    info.available = (
                        name.lower() in available_set or
                        any(a.startswith(name.split(":")[0]) for a in available_set)
                    )

            logger.info(f"[ModelRegistry] Ollama: {len(available)} modelo(s) dispon?vel(is)")
            return available
        except Exception as e:
            logger.warning(f"[ModelRegistry] Ollama n?o dispon?vel: {e}")
            # Marcar todos os modelos Ollama como indisponíveis
            for info in self._models.values():
                if info.provider == ModelProvider.OLLAMA:
                    info.available = False
            return []

    def get(self, model_name: str) -> Optional[ModelInfo]:
        return self._models.get(model_name)

    def best_local_model(self, task_type: str = "code") -> Optional[ModelInfo]:
        """
        Retorna o melhor modelo local disponível para um tipo de tarefa.
        Preferência: modelos recomendados para o tipo, depois genéricos.
        """
        candidates = [
            info for info in self._models.values()
            if info.provider == ModelProvider.OLLAMA and info.available
        ]

        # Ordenar por relevância ao tipo de tarefa
        def relevance(m: ModelInfo) -> int:
            return 1 if task_type in m.recommended_for else 0

        candidates.sort(key=relevance, reverse=True)
        return candidates[0] if candidates else None

    def list_available(self) -> list[ModelInfo]:
        return [m for m in self._models.values() if m.available]

    def has_local_models(self) -> bool:
        return any(
            m.provider == ModelProvider.OLLAMA and m.available
            for m in self._models.values()
        )


# Singleton global
registry = ModelRegistry()
