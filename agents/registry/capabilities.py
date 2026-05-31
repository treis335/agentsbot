"""
agents/registry/capabilities.py — Compat module.

O notifier importa get_registry daqui.
Redireciona para o CapabilityRegistry real.
"""
from agents.capability_registry import get_registry as _get_registry


def get_registry():
    """Retorna o registry de capabilities global."""
    return _get_registry()
