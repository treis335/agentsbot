"""
core/bus.py — Event Bus persistente (Batch 3).

Substitui o EventBus in-memory pelo PersistentEventBus que usa
write-ahead log em ficheiro JSONL. API 100% compatível — nenhum
chamador precisa de mudar.

Ao arrancar, chamar replay_pending_events(bus) em main.py para
re-entregar eventos não processados de crashes anteriores.
"""
from core.persistent_bus import PersistentEventBus

# Re-exportar EventBus como alias para compatibilidade
# (core/orchestrator.py faz "from .bus import bus, EventBus")
EventBus = PersistentEventBus

# Instância global — todos os módulos importam daqui
bus = PersistentEventBus()
