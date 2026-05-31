"""
inference/local_client.py — Cliente Ollama compatível com a interface OpenAI.

Usa a API REST do Ollama (/api/chat) mas expõe o mesmo contrato
que o AsyncOpenAI, para que o executor não precise de saber de nada.

Modelos recomendados:
    qwen2.5-coder:7b   — código (rápido, leve)
    qwen2.5-coder:14b  — código mais complexo
    llama3.2:3b        — texto simples e classificação
    mistral:7b         — raciocínio geral

Exemplo:
    client = OllamaClient()
    resp = await client.chat.completions.create(
        model="qwen2.5-coder:7b",
        messages=[{"role": "user", "content": "Olá"}],
    )
    print(resp.choices[0].message.content)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False
    aiohttp = None  # type: ignore


logger = logging.getLogger(__name__)


# --- RESPONSE MODELS (mimetizam openai) ----------------------------------------

@dataclass
class ChatMessage:
    role: str
    content: str
    tool_calls: list = field(default_factory=list)

    def model_dump(self, exclude_none=False) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class Choice:
    message: ChatMessage
    finish_reason: str = "stop"
    index: int = 0


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatCompletion:
    choices: list[Choice]
    usage: Optional[Usage] = None
    model: str = ""
    created: int = 0

    @property
    def id(self) -> str:
        return f"ollama-{self.created}"


class ChatCompletions:
    """Imita client.chat.completions do openai."""

    def __init__(self, base_url: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def create(
        self,
        model: str,
        messages: list[dict],
        tools: Optional[list] = None,
        tool_choice: str = "auto",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs,
    ) -> ChatCompletion:
        """
        Chama o endpoint /api/chat do Ollama.
        Tools são ignorados — Ollama não suporta function calling nativo.
        O executor é responsável por adaptar (ver router.py).
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        url = f"{self.base_url}/api/chat"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(f"Ollama HTTP {resp.status}: {text[:200]}")
                    data = await resp.json()
        except aiohttp.ClientConnectorError as e:
            raise RuntimeError(f"Ollama n?o est? acess?vel em {self.base_url}: {e}")

        content = data.get("message", {}).get("content", "")
        role = data.get("message", {}).get("role", "assistant")

        # Tokens (Ollama usa nomes ligeiramente diferentes)
        usage = Usage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        )

        return ChatCompletion(
            choices=[Choice(
                message=ChatMessage(role=role, content=content),
                finish_reason="stop",
            )],
            usage=usage,
            model=model,
            created=int(datetime.now().timestamp()),
        )


class ChatNamespace:
    def __init__(self, completions: ChatCompletions):
        self.completions = completions


class OllamaClient:
    """
    Cliente Ollama com interface idêntica ao AsyncOpenAI.

    Uso:
        client = OllamaClient(base_url="http://localhost:11434")
        resp = await client.chat.completions.create(model="qwen2.5-coder:7b", ...)
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120):
        self.base_url = base_url
        completions = ChatCompletions(base_url, timeout)
        self.chat = ChatNamespace(completions)

    async def is_available(self) -> bool:
        """Verifica se o servidor Ollama está a correr E tem o modelo disponível."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3)
            ) as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    # Verificar se o modelo configurado existe
                    model = self.model
                    # Match exacto ou prefixo (ex: qwen2.5-coder:7b vs qwen2.5-coder)
                    available = any(
                        m == model or m.startswith(model.split(":")[0])
                        for m in models
                    )
                    if not available:
                        logger.warning(
                            f"[OllamaClient] Ollama a correr mas modelo '{model}' "
                            f"não encontrado. Disponíveis: {models}"
                        )
                    return available
        except Exception:
            return False

    async def get_best_available_model(self) -> str:
        """
        Retorna o melhor modelo disponível localmente.
        Tenta o modelo configurado primeiro, depois alternativas leves.
        """
        fallback_models = [
            self.model,
            "qwen2.5-coder:7b",
            "qwen2.5:7b",
            "qwen2.5-coder:3b",
            "qwen2.5:3b",
            "llama3.2:3b",
            "llama3.2:1b",
            "phi3:mini",
            "phi3.5:mini",
            "tinyllama:latest",
        ]
        try:
            models = await self.list_models()
            if not models:
                return self.model
            for candidate in fallback_models:
                # Match exacto ou por prefixo
                for available in models:
                    if available == candidate or available.startswith(candidate.split(":")[0]):
                        logger.info(f"[OllamaClient] Usando modelo: {available}")
                        return available
            # Usar o primeiro disponível
            logger.info(f"[OllamaClient] Usando primeiro modelo disponível: {models[0]}")
            return models[0]
        except Exception:
            return self.model

    async def list_models(self) -> list[str]:
        """Retorna modelos disponíveis localmente."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Faz pull de um modelo Ollama (blocking, pode demorar).
        Retorna True se sucesso.
        """
        url = f"{self.base_url}/api/pull"
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=600)
            ) as session:
                async with session.post(url, json={"name": model_name, "stream": False}) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"[Ollama] Erro ao fazer pull de {model_name}: {e}")
            return False
