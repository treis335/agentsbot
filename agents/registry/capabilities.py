"""
agents/registry/capabilities.py — Compat module.

O notifier importa get_registry daqui.
Redireciona para o CapabilityRegistry real.
"""
from agents.capability_registry import capability_registry


def get_registry():
    """Retorna o registry de capabilities global."""
    return capability_registry
