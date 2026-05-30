"""
memory/loop_memory.py — Memória episódica do loop autónomo.

Grava cada execução e fornece contexto relevante antes de cada nova tarefa:
- O que já foi tentado (e como correu)
- Lições extraídas de falhas passadas
- Padrões de sucesso a reutilizar
- Estado persistente entre ciclos (tarefas multi-ciclo)

Usado por autonomous_loop._execute_task_real() para:
  1. Injectar contexto no prompt antes de executar
  2. Gravar resultado após executar
  3. Não repetir o que já falhou

Formato de cada episódio:
  {
    "task_id": "...",
    "task_desc": "...",
    "agent": "developer",
    "timestamp": "ISO",
    "success": true,
    "result_summary": "...",
    "lesson": "..."   # extraído automaticamente de falhas
  }
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_EPISODES_FILE = Path("memory") / "loop_episodes.json"
_MAX_EPISODES  = 200   # máximo em memória
_CONTEXT_LIMIT = 5     # episódios a mostrar por tarefa


class LoopMemory:
    """
    Memória episódica do loop autónomo.
    Singleton — partilhado por todos os ciclos.
    """

    def __init__(self):
        self._episodes: list[dict] = self._load()

    # -- Persistência -----------------------------------------------------------

    def _load(self) -> list[dict]:
        try:
            if _EPISODES_FILE.exists():
                return json.loads(_EPISODES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save(self) -> None:
        _EPISODES_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Manter só os mais recentes
        data = self._episodes[-_MAX_EPISODES:]
        _EPISODES_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # -- Escrita ----------------------------------------------------------------

    def record(
        self,
        task_id: str,
        task_desc: str,
        agent: str,
        success: bool,
        result: str,
    ) -> None:
        """Grava o resultado de uma execução."""
        lesson = ""
        if not success:
            lesson = self._extract_lesson(task_desc, result)

        episode = {
            "task_id":      task_id,
            "task_desc":    task_desc[:200],
            "agent":        agent,
            "timestamp":    datetime.now().isoformat(),
            "success":      success,
            "result_summary": str(result)[:400],
            "lesson":       lesson,
        }
        self._episodes.append(episode)
        self._save()
        logger.debug(f"[LoopMemory] Gravado: {task_id} success={success}")

        # Actualizar índice semântico em tempo real
        try:
            from memory.semantic_search import get_index
            idx = get_index(auto_build=False)
            if idx._built:
                text = f"{task_desc} {str(result)[:200]} {lesson}"
                idx.add_document("episode", text.strip(), {
                    "agent": agent,
                    "success": success,
                    "task_desc": task_desc[:200],
                    "lesson": lesson,
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception:
            pass

    def _extract_lesson(self, task: str, result: str) -> str:
        """Extrai lição de uma falha por heurísticas locais (sem LLM)."""
        r = result.lower()
        if "modulenotfounderror" in r or "importerror" in r:
            mod = re.search(r"no module named '([^']+)'", r)
            return f"Módulo não instalado: {mod.group(1) if mod else 'desconhecido'}. Usar pip install primeiro."
        if "filenotfounderror" in r:
            return "Ficheiro não encontrado. Verificar caminho antes de ler."
        if "permissionerror" in r:
            return "Sem permissão. Verificar permissões do ficheiro/directório."
        if "syntaxerror" in r:
            return "Erro de sintaxe no código gerado. Testar com py_compile antes de usar."
        if "timeout" in r:
            return "Operação demorou demasiado. Dividir em passos menores."
        if "traceback" in r or "exception" in r:
            # Tentar extrair a última linha do traceback
            lines = result.strip().splitlines()
            last = next((l for l in reversed(lines) if l.strip()), "")
            return f"Excepção: {last[:100]}"
        if "returncode: 1" in r or "returncode: 2" in r:
            return "Comando shell falhou. Verificar sintaxe e permissões."
        return "Tarefa falhou. Tentar abordagem diferente."

    # -- Leitura / Contexto -----------------------------------------------------

    def get_context_for_task(self, task_desc: str, task_id: str = "") -> str:
        """
        Retorna contexto relevante para injectar no prompt antes de executar.
        Inclui: tentativas anteriores desta tarefa, lições de falhas similares,
        e o que funcionou bem em tarefas parecidas.
        """
        lines = []

        # 1. Tentativas anteriores DESTA tarefa exacta
        same = [
            e for e in self._episodes
            if e.get("task_id") == task_id or
               self._similarity(e.get("task_desc", ""), task_desc) > 0.5
        ]
        if same:
            lines.append("## Tentativas anteriores desta tarefa")
            for e in same[-3:]:
                icon = "[OK]" if e["success"] else "[X]"
                ts = e["timestamp"][:16].replace("T", " ")
                lines.append(f"- {icon} [{ts}] agente={e['agent']}: {e['result_summary'][:120]}")
                if e.get("lesson"):
                    lines.append(f"  [!] Lição: {e['lesson']}")

        # 2. Lições de falhas com palavras em comum
        lessons = self._relevant_lessons(task_desc, limit=3)
        if lessons:
            lines.append("\n## Lições de tarefas similares")
            for l in lessons:
                lines.append(f"- {l}")

        # 3. O que funcionou bem (padrões de sucesso)
        recent_success = [e for e in self._episodes[-20:] if e["success"]]
        if recent_success:
            agent_counts: dict[str, int] = {}
            for e in recent_success:
                agent_counts[e["agent"]] = agent_counts.get(e["agent"], 0) + 1
            best = max(agent_counts, key=lambda k: agent_counts[k])
            lines.append(f"\n## Nota: agente '{best}' teve mais sucesso recentemente ({agent_counts[best]} tarefas).")

        if not lines:
            return ""

        return "\n## MEMÓRIA DE EXECUÇÕES ANTERIORES\n" + "\n".join(lines) + "\n"

    def _similarity(self, a: str, b: str) -> float:
        """
        Similaridade semântica TF-IDF + cosine (via SemanticIndex).
        Fallback para Jaccard se índice não disponível.
        """
        try:
            from memory.semantic_search import get_index
            idx = get_index(auto_build=False)
            if idx._built and idx._idf:
                import math
                from collections import defaultdict
                def tfidf(tokens):
                    tf = defaultdict(float)
                    for t in tokens: tf[t] += 1
                    n = len(tokens) or 1
                    return {t: (c/n) * idx._idf.get(t, 1.0) for t, c in tf.items()}
                from memory.semantic_search import _tokenize
                va = tfidf(_tokenize(a))
                vb = tfidf(_tokenize(b))
                common = set(va) & set(vb)
                if not common:
                    return 0.0
                dot = sum(va[k]*vb[k] for k in common)
                mag_a = math.sqrt(sum(x*x for x in va.values()))
                mag_b = math.sqrt(sum(x*x for x in vb.values()))
                if mag_a == 0 or mag_b == 0:
                    return 0.0
                return dot / (mag_a * mag_b)
        except Exception:
            pass
        # Fallback Jaccard
        wa = set(a.lower().split())
        wb = set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def _relevant_lessons(self, task: str, limit: int = 3) -> list[str]:
        """Lições de falhas com palavras em comum com a tarefa."""
        task_words = set(task.lower().split())
        lessons = []
        for e in reversed(self._episodes):
            lesson = e.get("lesson", "")
            if not lesson or e.get("success"):
                continue
            ep_words = set(e.get("task_desc", "").lower().split())
            if len(task_words & ep_words) >= 2:
                if lesson not in lessons:
                    lessons.append(lesson)
            if len(lessons) >= limit:
                break
        return lessons

    # -- Estatísticas -----------------------------------------------------------

    def stats(self) -> dict:
        """Estatísticas da memória (para dashboard e self-improve)."""
        total = len(self._episodes)
        success = sum(1 for e in self._episodes if e.get("success"))
        failures = total - success
        by_agent: dict[str, dict] = {}
        for e in self._episodes:
            ag = e.get("agent", "?")
            if ag not in by_agent:
                by_agent[ag] = {"total": 0, "success": 0}
            by_agent[ag]["total"] += 1
            if e.get("success"):
                by_agent[ag]["success"] += 1
        return {
            "total_episodes": total,
            "success": success,
            "failures": failures,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "by_agent": by_agent,
        }

    def recent_failures(self, limit: int = 5) -> list[dict]:
        """Falhas recentes para o dashboard."""
        return [e for e in reversed(self._episodes) if not e.get("success")][:limit]


# Singleton global
_instance: Optional[LoopMemory] = None

def get_loop_memory() -> LoopMemory:
    global _instance
    if _instance is None:
        _instance = LoopMemory()
    return _instance
