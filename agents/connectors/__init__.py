"""
agents/connectors/__init__.py — Conectores do ecossistema Correoto

Módulos de conexão entre agentes e sistemas externos:
- mcp: Model Context Protocol (comunicação entre agentes)
- cache: Reasoning Cache Layer (evita recomputar respostas)
- learning_loop: Self-Improving Learning Loop (aprender com erros)
- skills: Modular Skills System (skills descobertas dinamicamente)
- provider: Multi-Provider Support (DeepSeek, OpenAI, Anthropic)
"""

from .mcp import MCPServer, MCPClient, get_mcp_server
from .cache import ReasoningCache, get_cache
from .learning_loop import LearningLoop, get_learning_loop
from .skills import Skill, SkillsRegistry, get_skills_registry
from .provider import (
    LLMProvider, DeepSeekProvider, OpenAIProvider, AnthropicProvider,
    ProviderManager, get_provider_manager
)

__all__ = [
    "MCPServer", "MCPClient", "get_mcp_server",
    "ReasoningCache", "get_cache",
    "LearningLoop", "get_learning_loop",
    "Skill", "SkillsRegistry", "get_skills_registry",
    "LLMProvider", "DeepSeekProvider", "OpenAIProvider", "AnthropicProvider",
    "ProviderManager", "get_provider_manager"
]
