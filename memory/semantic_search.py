"""
memory/semantic_search.py — Memória semântica com pesquisa por significado.

Usa TF-IDF + cosine similarity — sem dependências externas.
Permite perguntar "o que aprendi sobre timeouts?" e obter
os episódios mais relevantes, não os mais recentes.

Indexa automaticamente episódios, lições, debates e decisões.
"""

import json
import logging
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Stopwords PT+EN para não poluir o índice
STOPWORDS = {
    "a","o","e","de","do","da","em","um","uma","que","com","por","para",
    "se","não","na","no","as","os","mais","mas","foi","ao","isso","este",
    "esta","já","como","the","is","in","of","to","and","for","with","that",
    "this","it","was","are","be","has","have","from","or","an","at","by",
    "we","can","will","do","if","on","but","not","as","so","all","been",
    "seu","sua","suas","seus","ele","ela","eles","elas","me","te","nos",
    "vos","lhe","lhes","muito","bem","também","ainda","só","mesmo","cada",
    "vai","vou","está","estão","tem","têm","ter","ser","fazer","quando",
}


def _tokenize(text: str) -> list[str]:
    """Tokeniza texto em palavras relevantes."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = [w for w in text.split() if len(w) > 2 and w not in STOPWORDS]
    return tokens


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Calcula vector TF-IDF para uma lista de tokens."""
    tf: dict[str, float] = defaultdict(float)
    for t in tokens:
        tf[t] += 1.0
    n = len(tokens) or 1
    return {t: (count / n) * idf.get(t, 1.0) for t, count in tf.items()}


def _cosine(v1: dict, v2: dict) -> float:
    """Cosine similarity entre dois vectores esparsos."""
    common = set(v1) & set(v2)
    if not common:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in common)
    mag1 = math.sqrt(sum(x * x for x in v1.values()))
    mag2 = math.sqrt(sum(x * x for x in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class SemanticIndex:
    """
    Índice semântico TF-IDF sobre todos os documentos da memória.

    Um "documento" pode ser:
    - Episódio (task_desc + lesson + result_summary)
    - Debate (topic + synthesis + contributions)
    - Lição extraída
    - Decisão arquitectural

    Uso:
        idx = SemanticIndex()
        idx.build()  # indexa tudo
        results = idx.search("como resolver timeouts em git push", top_k=5)
    """

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.index_file = self.memory_dir / "semantic_index.json"
        self._docs: list[dict] = []       # {id, type, text, tokens, metadata}
        self._idf: dict[str, float] = {}  # term → IDF score
        self._built = False

    # ── Build ──────────────────────────────────────────────────────────────────

    def build(self, force: bool = False) -> int:
        """
        Constrói o índice a partir de todos os ficheiros de memória.
        Carrega do cache se existir e não for forçado rebuild.

        Returns:
            Número de documentos indexados
        """
        if not force and self.index_file.exists():
            try:
                cached = json.loads(self.index_file.read_text(encoding="utf-8"))
                self._docs = cached["docs"]
                self._idf = cached["idf"]
                self._built = True
                logger.debug(f"[SemanticIndex] Carregado cache: {len(self._docs)} docs")
                return len(self._docs)
            except Exception:
                pass

        self._docs = []
        self._collect_episodes()
        self._collect_debates()
        self._collect_lessons()
        self._collect_decisions()
        self._compute_idf()
        self._built = True
        self._save_index()
        logger.info(f"[SemanticIndex] Construído: {len(self._docs)} documentos")
        return len(self._docs)

    def _collect_episodes(self):
        """Indexa episódios da memória de loop."""
        episodes_file = self.memory_dir / "loop_episodes.json"
        if not episodes_file.exists():
            return
        try:
            episodes = json.loads(episodes_file.read_text(encoding="utf-8"))
            for ep in episodes:
                text_parts = [
                    ep.get("task_desc", ""),
                    ep.get("lesson", ""),
                    ep.get("result_summary", ""),
                ]
                text = " ".join(p for p in text_parts if p)
                if len(text) < 10:
                    continue
                self._docs.append({
                    "id": ep.get("task_id", f"ep_{len(self._docs)}"),
                    "type": "episode",
                    "text": text,
                    "tokens": _tokenize(text),
                    "metadata": {
                        "agent": ep.get("agent", "?"),
                        "success": ep.get("success", True),
                        "timestamp": ep.get("timestamp", ""),
                        "task_desc": ep.get("task_desc", "")[:200],
                        "lesson": ep.get("lesson", ""),
                    }
                })
        except Exception as e:
            logger.warning(f"[SemanticIndex] Erro episódios: {e}")

    def _collect_debates(self):
        """Indexa debates do organic_mind."""
        debates_dir = self.memory_dir / "debates"
        if not debates_dir.exists():
            return
        for f in debates_dir.glob("debate_*.json"):
            try:
                debate = json.loads(f.read_text(encoding="utf-8"))
                parts = [debate.get("topic", ""), debate.get("synthesis", "")]
                for c in debate.get("contributions", []):
                    parts.append(c.get("thought", ""))
                text = " ".join(p for p in parts if p)
                if len(text) < 10:
                    continue
                self._docs.append({
                    "id": f"debate_{f.stem}",
                    "type": "debate",
                    "text": text,
                    "tokens": _tokenize(text),
                    "metadata": {
                        "topic": debate.get("topic", ""),
                        "synthesis": debate.get("synthesis", "")[:200],
                        "timestamp": debate.get("ts", ""),
                        "n_tasks": len(debate.get("tasks", [])),
                    }
                })
            except Exception as e:
                logger.debug(f"[SemanticIndex] Debate {f}: {e}")

    def _collect_lessons(self):
        """Indexa lições extraídas."""
        lessons_file = self.memory_dir / "lessons" / "extracted_lessons.json"
        if not lessons_file.exists():
            return
        try:
            lessons = json.loads(lessons_file.read_text(encoding="utf-8"))
            for l in lessons:
                text = l.get("lesson", "")
                if len(text) < 10:
                    continue
                self._docs.append({
                    "id": f"lesson_{len(self._docs)}",
                    "type": "lesson",
                    "text": text,
                    "tokens": _tokenize(text),
                    "metadata": {
                        "agent": l.get("agent", "?"),
                        "lesson": text,
                        "timestamp": l.get("timestamp", ""),
                    }
                })
        except Exception as e:
            logger.debug(f"[SemanticIndex] Lições: {e}")

    def _collect_decisions(self):
        """Indexa decisões arquitecturais da memória semântica."""
        from memory.semantica import SemanticMemory
        try:
            sm = SemanticMemory()
            for d in sm.get_decisions(limit=50):
                text = f"{d.get('decision', '')} {d.get('rationale', '')}"
                if len(text) < 10:
                    continue
                self._docs.append({
                    "id": f"decision_{len(self._docs)}",
                    "type": "decision",
                    "text": text,
                    "tokens": _tokenize(text),
                    "metadata": {
                        "decision": d.get("decision", "")[:150],
                        "timestamp": d.get("timestamp", ""),
                    }
                })
        except Exception as e:
            logger.debug(f"[SemanticIndex] Decisões: {e}")

    def _compute_idf(self):
        """Calcula IDF para todos os termos do corpus."""
        n_docs = len(self._docs)
        if n_docs == 0:
            return
        df: dict[str, int] = defaultdict(int)
        for doc in self._docs:
            for term in set(doc["tokens"]):
                df[term] += 1
        self._idf = {
            term: math.log((n_docs + 1) / (count + 1)) + 1.0
            for term, count in df.items()
        }

    def _save_index(self):
        """Persiste índice em disco."""
        try:
            self.memory_dir.mkdir(exist_ok=True)
            self.index_file.write_text(
                json.dumps({"docs": self._docs, "idf": self._idf},
                           ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"[SemanticIndex] Erro ao guardar índice: {e}")

    # ── Search ─────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        min_score: float = 0.05,
    ) -> list[dict]:
        """
        Pesquisa semântica por significado.

        Args:
            query: Pergunta ou descrição em linguagem natural
            top_k: Número máximo de resultados
            doc_type: Filtrar por tipo ("episode", "debate", "lesson", "decision")
            min_score: Score mínimo de similaridade (0-1)

        Returns:
            Lista de {score, type, metadata, text_preview} ordenada por relevância
        """
        if not self._built:
            self.build()

        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        q_vec = _tfidf_vector(q_tokens, self._idf)

        scored = []
        for doc in self._docs:
            if doc_type and doc["type"] != doc_type:
                continue
            if not doc["tokens"]:
                continue
            d_vec = _tfidf_vector(doc["tokens"], self._idf)
            score = _cosine(q_vec, d_vec)
            if score >= min_score:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "score": round(s, 4),
                "type": doc["type"],
                "metadata": doc["metadata"],
                "text_preview": doc["text"][:200],
            }
            for s, doc in scored[:top_k]
        ]

    def search_for_prompt(self, query: str, top_k: int = 4) -> str:
        """
        Pesquisa e formata resultados para injecção num system prompt.

        Returns:
            Bloco de texto formatado com contexto relevante, ou "" se vazio
        """
        results = self.search(query, top_k=top_k)
        if not results:
            return ""

        lines = ["\n## MEMÓRIA SEMÂNTICA — contexto relevante para esta tarefa\n"]
        for r in results:
            t = r["type"]
            m = r["metadata"]
            score = r["score"]

            if t == "episode":
                status = "✅" if m.get("success") else "❌"
                lines.append(
                    f"{status} [{m.get('agent','?')}] {m.get('task_desc','')[:100]}"
                )
                if m.get("lesson"):
                    lines.append(f"   → Lição: {m['lesson']}")
            elif t == "lesson":
                lines.append(f"📚 Lição: {m.get('lesson','')[:120]}")
            elif t == "debate":
                lines.append(
                    f"💬 Debate '{m.get('topic','')[:60]}': {m.get('synthesis','')[:100]}"
                )
            elif t == "decision":
                lines.append(f"🏗️ Decisão: {m.get('decision','')[:120]}")

        return "\n".join(lines) + "\n"

    def add_document(self, doc_type: str, text: str, metadata: dict = None) -> str:
        """
        Adiciona documento ao índice em runtime (sem rebuild completo).

        Returns:
            ID do documento criado
        """
        if not self._built:
            self.build()

        doc_id = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        tokens = _tokenize(text)

        # Actualizar IDF incrementalmente
        n_docs = len(self._docs) + 1
        for term in set(tokens):
            df_approx = sum(1 for d in self._docs if term in d["tokens"]) + 1
            self._idf[term] = math.log((n_docs + 1) / (df_approx + 1)) + 1.0

        doc = {
            "id": doc_id,
            "type": doc_type,
            "text": text,
            "tokens": tokens,
            "metadata": metadata or {},
        }
        self._docs.append(doc)
        self._save_index()
        return doc_id

    def rebuild(self) -> int:
        """Força rebuild completo do índice."""
        return self.build(force=True)

    def stats(self) -> dict:
        """Estatísticas do índice."""
        if not self._built:
            self.build()
        by_type: dict[str, int] = defaultdict(int)
        for doc in self._docs:
            by_type[doc["type"]] += 1
        return {
            "total_docs": len(self._docs),
            "vocab_size": len(self._idf),
            "by_type": dict(by_type),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_index: Optional[SemanticIndex] = None


def get_index(auto_build: bool = True) -> SemanticIndex:
    """Retorna instância global do índice (lazy init)."""
    global _index
    if _index is None:
        _index = SemanticIndex()
        if auto_build:
            _index.build()
    return _index


def search(query: str, top_k: int = 5, doc_type: str = None) -> list[dict]:
    """Atalho: pesquisa semântica directa."""
    return get_index().search(query, top_k=top_k, doc_type=doc_type)


def search_for_prompt(query: str, top_k: int = 4) -> str:
    """Atalho: pesquisa formatada para prompt."""
    return get_index().search_for_prompt(query, top_k=top_k)
