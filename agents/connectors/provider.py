"""
agents/connectors/provider.py — Multi-Provider Support

Suporte a múltiplos providers LLM (DeepSeek, OpenAI, Anthropic).
Inspirado no Crush (multi-model switching) e Claude Code (provider-agnostic).
"""
import json
import os
from typing import Optional, Any
from datetime import datetime

class LLMProvider:
    """Provider LLM abstrato."""
    
    def __init__(self, name: str, api_key: str, base_url: str):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.models = []
    
    async def chat(self, messages: list, model: str, **kwargs) -> dict:
        """Envia chat para o provider. Implementar nas subclasses."""
        raise NotImplementedError
    
    def list_models(self) -> list:
        return self.models


class DeepSeekProvider(LLMProvider):
    """Provider DeepSeek."""
    
    def __init__(self, api_key: str = None):
        super().__init__(
            name="deepseek",
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        )
        self.models = [
            {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro", "context": 1000000, "reasoning": True},
            {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "context": 1000000, "reasoning": True}
        ]
    
    async def chat(self, messages: list, model: str = "deepseek-v4-pro", **kwargs) -> dict:
        import urllib.request
        import json
        
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        if kwargs.get("reasoning_effort"):
            payload["reasoning_effort"] = kwargs["reasoning_effort"]
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return {
                    "content": result["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": self.name,
                    "usage": result.get("usage", {})
                }
        except Exception as e:
            return {"error": str(e), "model": model, "provider": self.name}


class OpenAIProvider(LLMProvider):
    """Provider OpenAI."""
    
    def __init__(self, api_key: str = None):
        super().__init__(
            name="openai",
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        )
        self.models = [
            {"id": "gpt-4o", "name": "GPT-4o", "context": 128000, "reasoning": False},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context": 128000, "reasoning": False}
        ]


class AnthropicProvider(LLMProvider):
    """Provider Anthropic (via DeepSeek Anthropic API)."""
    
    def __init__(self, api_key: str = None):
        super().__init__(
            name="anthropic",
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
        )


class ProviderManager:
    """Gestor de múltiplos providers."""
    
    def __init__(self):
        self._providers = {}
        self._default = None
        self._init_defaults()
    
    def _init_defaults(self):
        """Inicializa providers padrão."""
        deepseek = DeepSeekProvider()
        if deepseek.api_key:
            self.register(deepseek)
            self._default = "deepseek"
        
        openai = OpenAIProvider()
        if openai.api_key:
            self.register(openai)
    
    def register(self, provider: LLMProvider):
        """Regista um provider."""
        self._providers[provider.name] = provider
    
    def get(self, name: str) -> Optional[LLMProvider]:
        """Obtém um provider pelo nome."""
        return self._providers.get(name)
    
    def get_default(self) -> Optional[LLMProvider]:
        """Obtém o provider padrão."""
        if self._default and self._default in self._providers:
            return self._providers[self._default]
        if self._providers:
            return list(self._providers.values())[0]
        return None
    
    def set_default(self, name: str):
        """Define o provider padrão."""
        if name in self._providers:
            self._default = name
    
    def list_providers(self) -> list:
        """Lista todos os providers registados."""
        return [{"name": p.name, "models": p.models} for p in self._providers.values()]


# Instância global
_provider_manager = None

def get_provider_manager() -> ProviderManager:
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager
