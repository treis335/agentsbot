"""
core/memory.py — Memória Persistente de Conversa para o Supervisor.

Resolve o problema de "não me lembro do que já foi dito".
Cada interação é guardada num ficheiro JSONL com:
  - timestamp
  - speaker (human | supervisor | agente)
  - message
  - context (estado do ecossistema na altura)

Ao acordar, o Supervisor carrega o histórico e sabe o que já fez.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_DIR = Path("memory")
CONVERSATION_FILE = MEMORY_DIR / "conversation.jsonl"
MAX_HISTORY = 200  # Máximo de linhas no histórico


class ConversationMemory:
    """
    Memória de conversa persistente em JSONL.

    Uso:
        memory = ConversationMemory()
        memory.remember("human", "Quero um dashboard")
        last = memory.last_supervisor_message()
        history = memory.recent(10)
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = path or CONVERSATION_FILE
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if not self.path.exists():
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("")  # Ficheiro vazio
            logger.info(f"[Memory] Ficheiro criado: {self.path}")

    def remember(self, speaker: str, message: str, context: Optional[dict] = None):
        """
        Guarda uma mensagem no histórico.

        Args:
            speaker: "human" | "supervisor" | "agente"
            message: O conteúdo da mensagem
            context: Estado do ecossistema no momento (opcional)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "message": message,
            "context": context or {}
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._trim()
        except Exception as e:
            logger.error(f"[Memory] Erro ao guardar: {e}")

    def recent(self, n: int = 20) -> list[dict]:
        """Devolve as últimas N mensagens do histórico."""
        lines = self._read_all()
        return lines[-n:]

    def all(self) -> list[dict]:
        """Devolve todo o histórico."""
        return self._read_all()

    def last_supervisor_message(self) -> Optional[str]:
        """Devolve a última mensagem do Supervisor."""
        lines = self._read_all()
        for line in reversed(lines):
            if line.get("speaker") == "supervisor":
                return line.get("message", "")
        return None

    def last_human_message(self) -> Optional[str]:
        """Devolve a última mensagem do humano."""
        lines = self._read_all()
        for line in reversed(lines):
            if line.get("speaker") == "human":
                return line.get("message", "")
        return None

    def summary(self) -> str:
        """
        Devolve um resumo do histórico recente para contexto.
        Usado pelo Supervisor para saber o que já foi feito.
        """
        lines = self.recent(30)
        if not lines:
            return "Nenhum histórico disponível."

        parts = []
        for line in lines:
            speaker = line.get("speaker", "?")
            msg = line.get("message", "")
            # Trunca mensagens muito longas
            if len(msg) > 200:
                msg = msg[:200] + "..."
            parts.append(f"[{speaker}] {msg}")

        return "\n".join(parts)

    def count_human_messages(self) -> int:
        """Conta quantas mensagens o humano já enviou."""
        return sum(1 for l in self._read_all() if l.get("speaker") == "human")

    def search(self, keyword: str) -> list[dict]:
        """Procura mensagens que contenham uma palavra-chave."""
        return [
            l for l in self._read_all()
            if keyword.lower() in l.get("message", "").lower()
        ]

    def _read_all(self) -> list[dict]:
        """Lê todas as linhas do ficheiro JSONL."""
        if not self.path.exists():
            return []
        lines = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"[Memory] Erro ao ler: {e}")
        return lines

    def _trim(self):
        """Mantém apenas as últimas MAX_HISTORY linhas."""
        lines = self._read_all()
        if len(lines) > MAX_HISTORY:
            keep = lines[-MAX_HISTORY:]
            try:
                with open(self.path, "w", encoding="utf-8") as f:
                    for entry in keep:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                logger.info(f"[Memory] Histórico truncado para {MAX_HISTORY} entradas")
            except Exception as e:
                logger.error(f"[Memory] Erro ao truncar: {e}")

    def clear(self):
        """Limpa todo o histórico (uso em desenvolvimento)."""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("")
            logger.info("[Memory] Histórico limpo")
        except Exception as e:
            logger.error(f"[Memory] Erro ao limpar: {e}")


# Instância global — importas de qualquer lado
memory = ConversationMemory()
