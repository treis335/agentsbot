"""
memory/global_memory.py — Memoria global partilhada entre todos os agentes.

Armazena:
- Decisoes importantes
- Descobertas
- Estado do sistema
- Conhecimento comum
- Metricas globais

Inspirado no Memory Knowledge Graph do Mission Control.
"""
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.config import Config

logger = logging.getLogger(__name__)


class GlobalMemory:
    """
    Memoria global partilhada.

    Estrutura:
    {
        "decisions": [...],      # Decisoes importantes
        "discoveries": [...],    # Descobertas dos agentes
        "system_state": {...},   # Estado atual do sistema
        "knowledge": [...],      # Conhecimento acumulado
        "metrics": {...},        # Metricas globais
        "conversations": [...],  # Historico de conversas
    }
    """

    def __init__(self):
        self.config = Config
        self.memory_file = self.config.MEMORY_DIR / "global" / "shared_memory.json"
        self._data: dict = self._load()

    def _load(self) -> dict:
        """Carrega memoria do ficheiro."""
        if not self.memory_file.exists():
            return self._default()
        try:
            return json.loads(self.memory_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[GlobalMemory] Erro ao carregar: {e}")
            return self._default()

    def _save(self) -> None:
        """Guarda memoria no ficheiro com escrita atomica e locking."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.memory_file.with_suffix(".json.lock")
        # Tentar adquirir lock (max 5s)
        for attempt in range(50):
            try:
                # Criar lock file atomicamente
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                # Lock existe - verificar se e' stale (>2s)
                try:
                    age = time.time() - os.path.getmtime(lock_file)
                    if age > 2.0:
                        os.unlink(str(lock_file))
                        continue
                except:
                    pass
                time.sleep(0.1)
        else:
            # Timeout - forcar lock
            try:
                os.unlink(str(lock_file))
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
            except:
                pass
        try:
            # Escrita atomica: temp file -> rename
            tmp = tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=str(self.memory_file.parent),
                prefix='.shared_memory_tmp_', suffix='.json', delete=False
            )
            tmp.write(json.dumps(self._data, indent=2, ensure_ascii=False))
            tmp.close()
            os.replace(tmp.name, str(self.memory_file))
        finally:
            # Libertar lock
            try:
                os.unlink(str(lock_file))
            except:
                pass

    def _default(self) -> dict:
        return {
            "decisions": [],
            "discoveries": [],
            "system_state": {
                "version": "2.0",
                "last_start": datetime.now().isoformat(),
                "agents_count": 0,
                "tasks_count": 0,
            },
            "knowledge": [],
            "metrics": {
                "total_tool_calls": 0,
                "total_errors": 0,
                "total_tasks_completed": 0,
            },
            "conversations": [],
        }

    # --- Decisoes ---

    def add_decision(self, agent: str, decision: str, context: str = "") -> None:
        """Regista uma decisao importante."""
        self._data["decisions"].append({
            "agent": agent,
            "decision": decision,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()

    def get_decisions(self, limit: int = 20) -> list[dict]:
        """Retorna ultimas decisoes."""
        return self._data["decisions"][-limit:]

    # --- Descobertas ---

    def add_discovery(self, agent: str, discovery: str, category: str = "general") -> None:
        """Regista uma descoberta de um agente."""
        self._data["discoveries"].append({
            "agent": agent,
            "discovery": discovery,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()

    def get_discoveries(self, category: str = "", limit: int = 20) -> list[dict]:
        """Retorna descobertas, opcionalmente filtradas."""
        discoveries = self._data["discoveries"]
        if category:
            discoveries = [d for d in discoveries if d["category"] == category]
        return discoveries[-limit:]

    # --- Conhecimento ---

    def add_knowledge(self, topic: str, content: str, source: str = "system") -> None:
        """Adiciona conhecimento ao repositorio global."""
        # Verificar se ja existe sobre o mesmo topico
        for k in self._data["knowledge"]:
            if k["topic"].lower() == topic.lower():
                k["content"] = content
                k["source"] = source
                k["updated_at"] = datetime.now().isoformat()
                self._save()
                return

        self._data["knowledge"].append({
            "topic": topic,
            "content": content,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        })
        self._save()

    def get_knowledge(self, topic: str = "") -> list[dict]:
        """Busca conhecimento por topico."""
        if not topic:
            return self._data["knowledge"]
        return [k for k in self._data["knowledge"] if topic.lower() in k["topic"].lower()]

    # --- Estado do Sistema ---

    def update_system_state(self, key: str, value: Any) -> None:
        """Atualiza uma chave do estado do sistema."""
        self._data["system_state"][key] = value
        self._save()

    def get_system_state(self) -> dict:
        """Retorna estado atual do sistema."""
        return self._data["system_state"]

    # --- Metricas ---

    def increment_metric(self, metric: str, amount: int = 1) -> None:
        """Incrementa uma metrica."""
        if metric in self._data["metrics"]:
            self._data["metrics"][metric] += amount
        else:
            self._data["metrics"][metric] = amount
        self._save()

    def get_metrics(self) -> dict:
        """Retorna metricas globais."""
        return self._data["metrics"]

    # --- Util ---

    def get_all(self) -> dict:
        """Retorna toda a memoria."""
        return self._data

    def clear(self) -> None:
        """Limpa toda a memoria."""
        self._data = self._default()
        self._save()
        logger.info("[GlobalMemory] Memoria global limpa.")
