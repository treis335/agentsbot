"""
memory/lesson_extractor.py — Extrai "lições" dos logs episódicos existentes.

Processa o histórico já acumulado e produz lições estruturadas.
100% local — sem LLM, só heurísticas e padrões.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


# Padrões heurísticos para extrair lições
LESSON_PATTERNS = [
    # (regex no result/error, lição gerada)
    (r"permission denied", "Verificar permissões antes de escrever ficheiros"),
    (r"no such file", "Criar directórios pai com mkdir -p antes de escrever"),
    (r"syntax error", "Validar sintaxe Python antes de executar (python3 -m py_compile)"),
    (r"module not found|importerror", "Instalar dependências com pip antes de importar"),
    (r"git.*rejected", "Fazer git pull antes de push para evitar conflitos"),
    (r"timeout", "Aumentar timeout ou dividir tarefa em partes mais pequenas"),
    (r"json.*decode|invalid json", "Validar JSON antes de parsear — usar try/except"),
    (r"connection refused", "Verificar se o servidor está a correr antes de conectar"),
    (r"index.*out of range", "Verificar tamanho de listas antes de indexar"),
    (r"key error", "Usar .get() em vez de [] para aceder a dicionários"),
    (r"rate limit", "Adicionar sleep entre chamadas API para evitar rate limiting"),
    (r"encoding|utf", "Sempre abrir ficheiros com encoding='utf-8'"),
]


class LessonExtractor:
    """
    Extrai lições dos logs episódicos de todos os agentes.

    Produz um ficheiro de lições estruturadas em:
    memory/lessons/extracted_lessons.json
    """

    def __init__(self):
        self.episodic_dir = Config.MEMORY_DIR / "episodica"
        self.lessons_dir = Config.MEMORY_DIR / "lessons"
        self.lessons_file = self.lessons_dir / "extracted_lessons.json"

    def extract_from_episode(self, episode: dict) -> Optional[str]:
        """
        Extrai lição de um episódio individual.

        Args:
            episode: Entrada da memória episódica

        Returns:
            Lição como string, ou None se não extraível
        """
        # Já tem lição registada
        if episode.get("lesson"):
            return episode["lesson"]

        # Só extrair de falhas
        if episode.get("success", True):
            return None

        result = episode.get("episode", {}).get("result", "").lower()
        action = episode.get("episode", {}).get("action", "")

        # Aplicar padrões heurísticos
        for pattern, lesson in LESSON_PATTERNS:
            if re.search(pattern, result, re.IGNORECASE):
                return f"[{action}] {lesson}"

        # Lição genérica se há erro mas sem padrão
        if result and len(result) > 10:
            return f"[{action}] Falhou com: {result[:80]} ? investigar causa"

        return None

    def extract_all(self) -> list[dict]:
        """
        Processa todos os ficheiros episódicos e extrai lições.

        Returns:
            Lista de lições estruturadas
        """
        if not self.episodic_dir.exists():
            logger.warning("[LessonExtractor] Direct?rio epis?dico n?o existe")
            return []

        all_lessons = []
        seen_lessons: set[str] = set()  # Deduplicação

        for agent_file in self.episodic_dir.glob("*.json"):
            agent_id = agent_file.stem
            try:
                episodes = json.loads(agent_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.debug(f"[LessonExtractor] Erro ao ler {agent_file}: {e}")
                continue

            for ep in episodes:
                lesson_text = self.extract_from_episode(ep)
                if not lesson_text or lesson_text in seen_lessons:
                    continue

                seen_lessons.add(lesson_text)
                all_lessons.append({
                    "agent": agent_id,
                    "lesson": lesson_text,
                    "action": ep.get("episode", {}).get("action", "unknown"),
                    "success": ep.get("success", False),
                    "timestamp": ep.get("timestamp", ""),
                    "source": "episodic_extraction",
                })

        logger.info(f"[LessonExtractor] Extra?das {len(all_lessons)} li??es ?nicas de {self.episodic_dir}")
        return all_lessons

    def save_lessons(self, lessons: list[dict]) -> Path:
        """Persiste lições extraídas."""
        self.lessons_dir.mkdir(parents=True, exist_ok=True)

        # Mesclar com lições existentes
        existing = []
        if self.lessons_file.exists():
            try:
                existing = json.loads(self.lessons_file.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        # Deduplicar por texto da lição
        existing_texts = {l["lesson"] for l in existing}
        new_lessons = [l for l in lessons if l["lesson"] not in existing_texts]

        combined = existing + new_lessons
        self.lessons_file.write_text(
            json.dumps(combined, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"[LessonExtractor] {len(new_lessons)} novas li??es guardadas ({len(combined)} total)")
        return self.lessons_file

    def get_lessons_for_agent(self, agent_id: str, limit: int = 5) -> list[str]:
        """Retorna lições relevantes para um agente específico."""
        if not self.lessons_file.exists():
            return []
        try:
            all_lessons = json.loads(self.lessons_file.read_text(encoding="utf-8"))
        except Exception:
            return []

        # Priorizar lições do próprio agente, depois globais
        agent_lessons = [l["lesson"] for l in all_lessons if l.get("agent") == agent_id]
        other_lessons = [l["lesson"] for l in all_lessons if l.get("agent") != agent_id]

        combined = agent_lessons + other_lessons
        return list(dict.fromkeys(combined))[:limit]  # Deduplicar preservando ordem

    def run(self) -> dict:
        """
        Executa extracção completa e persiste.

        Returns:
            Stats da execução
        """
        lessons = self.extract_all()
        saved_path = self.save_lessons(lessons)
        return {
            "extracted": len(lessons),
            "saved_to": str(saved_path),
        }
