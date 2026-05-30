"""
inference/router.py — Router de inferência: DeepSeek vs Ollama local.

Decide por cada chamada se usa o modelo cloud (DeepSeek) ou local (Ollama)
com base no score de complexidade da tarefa.

Regra principal:
    score < ROUTING_THRESHOLD  ->  Ollama (gratuito, local)
    score >= ROUTING_THRESHOLD ->  DeepSeek (pago, cloud)

Fallback automático:
    Ollama indisponível ou timeout -> DeepSeek
    DeepSeek com erro de quota     -> Ollama (degraded mode)

Uso (no executor):
    router = InferenceRouter()
    client, model_name = await router.get_client(task_description)
    response = await client.chat.completions.create(model=model_name, ...)
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from core.config import Config
from inference.complexity_scorer import score_task, ComplexityResult
from inference.model_registry import registry, ModelProvider

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    use_local: bool
    model_name: str
    provider: str           # "ollama" | "deepseek"
    complexity_score: float
    complexity_label: str
    reason: str
    fallback: bool = False  # True se a decisão original foi invertida por fallback


class InferenceRouter:
    """
    Router de inferência com fallback automático.

    Mantém estado sobre disponibilidade do Ollama para
    não tentar chamar um servidor que sabemos estar em baixo.
    """

    def __init__(self):
        self.config = Config
        self._ollama_available: Optional[bool] = None  # None = desconhecido
        self._ollama_client = None
        self._deepseek_client = None
        self._stats = {"local": 0, "cloud": 0, "fallback": 0}

    # -- Clientes ----------------------------------------------------------------

    def _get_deepseek_client(self):
        if not self._deepseek_client:
            from openai import AsyncOpenAI
            self._deepseek_client = AsyncOpenAI(
                api_key=self.config.DEEPSEEK_API_KEY,
                base_url=self.config.DEEPSEEK_BASE_URL,
            )
        return self._deepseek_client

    def _get_ollama_client(self):
        if not self._ollama_client:
            from inference.local_client import OllamaClient
            self._ollama_client = OllamaClient(
                base_url=getattr(self.config, "OLLAMA_URL", "http://localhost:11434"),
                timeout=getattr(self.config, "OLLAMA_TIMEOUT", 120),
            )
        return self._ollama_client

    async def _check_ollama(self) -> bool:
        """Verifica disponibilidade do Ollama (com cache de 60s)."""
        if self._ollama_available is None:
            client = self._get_ollama_client()
            self._ollama_available = await client.is_available()
            if self._ollama_available:
                logger.info("[Router] Ollama dispon?vel [OK]")
            else:
                logger.warning("[Router] Ollama n?o dispon?vel ? usando DeepSeek")
        return self._ollama_available

    def invalidate_ollama_cache(self):
        """Força re-verificação do Ollama na próxima chamada."""
        self._ollama_available = None

    # -- Routing principal -------------------------------------------------------

    async def decide(
        self,
        task: str,
        context_size: int = 0,
        num_files: int = 0,
        past_failures: int = 0,
        force_local: bool = False,
        force_cloud: bool = False,
    ) -> RoutingDecision:
        """
        Decide onde executar a inferência.

        Args:
            task: descrição da tarefa
            context_size: tamanho do contexto em chars
            num_files: número de ficheiros envolvidos
            past_failures: falhas anteriores nesta tarefa
            force_local: forçar Ollama independente do score
            force_cloud: forçar DeepSeek independente do score

        Returns:
            RoutingDecision com cliente e modelo escolhidos
        """
        complexity = score_task(
            task,
            context_size=context_size,
            num_files=num_files,
            past_failures=past_failures,
        )

        # Override manual
        if force_cloud:
            return self._deepseek_decision(complexity, reason="forçado por force_cloud")
        if force_local:
            return await self._local_decision(complexity, reason="forçado por force_local")

        # Decisão automática por threshold
        threshold = getattr(self.config, "ROUTING_THRESHOLD", 0.4)
        if complexity.score < threshold:
            decision = await self._local_decision(complexity)
            if decision:
                return decision
            # Fallback: Ollama indisponível -> DeepSeek
            logger.warning("[Router] Ollama indispon?vel, fallback para DeepSeek")
            d = self._deepseek_decision(complexity, reason=f"fallback (Ollama off) ? {complexity.reason}")
            d.fallback = True
            self._stats["fallback"] += 1
            return d
        else:
            return self._deepseek_decision(complexity)

    async def _local_decision(
        self, complexity: ComplexityResult, reason: str = ""
    ) -> Optional[RoutingDecision]:
        """Tenta routing local. Retorna None se Ollama não disponível."""
        if not await self._check_ollama():
            return None

        # Escolher melhor modelo local
        task_type = "code" if complexity.label in ("low", "medium") else "general"
        model_info = registry.best_local_model(task_type)

        if not model_info:
            # Sem modelos locais registados -> fallback
            return None

        self._stats["local"] += 1
        return RoutingDecision(
            use_local=True,
            model_name=model_info.name,
            provider="ollama",
            complexity_score=complexity.score,
            complexity_label=complexity.label,
            reason=reason or f"score={complexity.score:.2f} < threshold ? {complexity.reason}",
        )

    def _deepseek_decision(
        self, complexity: ComplexityResult, reason: str = ""
    ) -> RoutingDecision:
        self._stats["cloud"] += 1
        model = getattr(self.config, "DEEPSEEK_MODEL", "deepseek-chat")
        return RoutingDecision(
            use_local=False,
            model_name=model,
            provider="deepseek",
            complexity_score=complexity.score,
            complexity_label=complexity.label,
            reason=reason or f"score={complexity.score:.2f} >= threshold ? {complexity.reason}",
        )

    # -- Interface de alto nível -------------------------------------------------

    async def get_client(self, task: str, **kwargs):
        """
        Retorna (client, model_name) para uma tarefa.
        O client é compatível com AsyncOpenAI.

        Uso no executor:
            client, model = await router.get_client(task_description)
            resp = await client.chat.completions.create(model=model, ...)
        """
        decision = await self.decide(task, **kwargs)

        if decision.use_local:
            client = self._get_ollama_client()
            logger.debug(f"[Router] LOCAL {decision.model_name} (score={decision.complexity_score:.2f})")
        else:
            client = self._get_deepseek_client()
            if decision.fallback:
                logger.debug(f"[Router] CLOUD fallback {decision.model_name}")
            else:
                logger.debug(f"[Router] CLOUD {decision.model_name} (score={decision.complexity_score:.2f})")

        return client, decision.model_name, decision

    def stats(self) -> dict:
        """Estatísticas de routing (para dashboard)."""
        total = sum(self._stats.values())
        pct_local = (self._stats["local"] / total * 100) if total else 0
        return {
            "total_calls": total,
            "local_calls": self._stats["local"],
            "cloud_calls": self._stats["cloud"],
            "fallback_calls": self._stats["fallback"],
            "pct_local": round(pct_local, 1),
            "estimated_savings_pct": round(pct_local, 1),
        }


# Singleton global (partilhado entre todos os executors)
router = InferenceRouter()
