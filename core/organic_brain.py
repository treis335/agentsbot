"""
core/organic_brain.py — O cérebro orgânico do ecossistema.

Em vez de 1 tarefa → 1 agente silencioso, aqui os agentes:
1. PENSAM em conjunto sobre o que fazer a seguir
2. DEBATEM abordagens diferentes
3. DECIDEM por consenso (ou voto do supervisor)
4. EXECUTAM com especialização
5. REPORTAM e APRENDEM colectivamente

É o coração do sistema orgânico — torna o ecossistema vivo.
"""
import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_DIR    = Path("memory")
DIALOGUE_LOG  = MEMORY_DIR / "global" / "agent_dialogues.jsonl"
THOUGHTS_FILE = MEMORY_DIR / "global" / "collective_thoughts.json"


# ── Personalidades dos agentes para diálogo ──────────────────────────────────

AGENT_PERSONALITIES = {
    "supervisor": {
        "emoji": "🧠",
        "voz": "Coordenador estratégico. Pensa no sistema como um todo. Faz perguntas difíceis.",
        "estilo": "directo, decisivo, questiona sempre 'porquê'",
    },
    "developer": {
        "emoji": "💻",
        "voz": "Implementador técnico. Pensa em código, APIs e soluções práticas.",
        "estilo": "pragmático, foca em 'como fazer', prefere soluções simples",
    },
    "arquiteto": {
        "emoji": "🏗️",
        "voz": "Pensador estrutural. Vê padrões, dependências e consequências a longo prazo.",
        "estilo": "cuidadoso, avisa sobre complexidade, pensa em escalabilidade",
    },
    "explorador": {
        "emoji": "🔭",
        "voz": "Curioso e inovador. Pesquisa o que existe no mundo e traz ideias novas.",
        "estilo": "entusiasmado, referencia tecnologias, propõe coisas inesperadas",
    },
    "auto_fixer": {
        "emoji": "🔧",
        "voz": "Pessimista construtivo. Encontra o que pode correr mal antes de acontecer.",
        "estilo": "céptico, alerta para edge cases, prefere estabilidade",
    },
    "qa_tester": {
        "emoji": "🧪",
        "voz": "Validador rigoroso. Pergunta sempre 'como sabemos que funciona?'",
        "estilo": "metódico, insiste em evidências, pede testes antes de declarar sucesso",
    },
    "auto_evolver": {
        "emoji": "🧬",
        "voz": "Visionário da evolução. Pensa em como o sistema pode melhorar a si próprio.",
        "estilo": "futurista, propõe mudanças radicais, menos conservador",
    },
    "brainstormer": {
        "emoji": "💡",
        "voz": "Gerador de ideias sem filtro. Quantidade antes de qualidade.",
        "estilo": "criativo, divergente, não tem medo de ideias absurdas",
    },
}


class OrganicBrain:
    """
    O cérebro colectivo do ecossistema.

    Orquestra conversas reais entre agentes usando LLM para cada um,
    com personalidades distintas, memória partilhada e decisões por consenso.
    """

    def __init__(self, num_agents_per_debate: int = 3):
        self.num_agents = num_agents_per_debate
        MEMORY_DIR.joinpath("global").mkdir(parents=True, exist_ok=True)
        DIALOGUE_LOG.parent.mkdir(parents=True, exist_ok=True)

    # ── API pública ────────────────────────────────────────────────────────────

    def run_collective_thought(self, context: str = "") -> dict:
        """
        Executa um ciclo de pensamento colectivo:
        1. Escolhe 3-4 agentes
        2. Cada um pensa sobre o contexto
        3. Debatem e chegam a uma decisão
        4. Retorna a decisão + próximas acções

        Returns:
            {
                "decision": str,
                "next_tasks": list,
                "dialogue": list,
                "agents": list,
            }
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._async_collective_thought(context))
        finally:
            loop.close()

    def run_agent_debate(self, topic: str, agents: list = None) -> str:
        """
        Debate curto entre 2-3 agentes sobre um tópico.
        Retorna o resumo do debate + decisão.
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._async_debate(topic, agents))
        finally:
            loop.close()

    # ── Implementação interna ──────────────────────────────────────────────────

    async def _async_collective_thought(self, context: str) -> dict:
        """Pensamento colectivo assíncrono."""
        from agents.llm_agent import _call_llm

        # Escolher agentes para este ciclo (sempre supervisor + 2-3 especialistas)
        specialists = [a for a in AGENT_PERSONALITIES if a != "supervisor"]
        chosen = ["supervisor"] + random.sample(specialists, min(3, len(specialists)))

        dialogue = []
        all_ideas = []

        # Ler estado do sistema para contexto
        system_state = self._get_system_state()

        # Fase 1: cada agente pensa individualmente
        logger.info(f"[OrganicBrain] 🧠 Pensamento colectivo — {', '.join(chosen)}")

        for agent_name in chosen:
            p = AGENT_PERSONALITIES[agent_name]
            thought = await self._agent_think(agent_name, p, context, system_state, _call_llm)
            if thought:
                dialogue.append({
                    "agent": agent_name,
                    "emoji": p["emoji"],
                    "thought": thought,
                    "phase": "think",
                    "timestamp": datetime.now().isoformat(),
                })
                all_ideas.append(f"{p['emoji']} **{agent_name}**: {thought}")
                logger.info(f"[{p['emoji']} {agent_name}] {thought[:120]}")

        # Fase 2: debate — 1-2 agentes respondem às ideias dos outros
        if len(dialogue) >= 2:
            responder = random.choice([a for a in chosen if a != "supervisor"])
            p = AGENT_PERSONALITIES[responder]
            debate_context = "\n".join(all_ideas[:3])
            response = await self._agent_respond(responder, p, debate_context, _call_llm)
            if response:
                dialogue.append({
                    "agent": responder,
                    "emoji": p["emoji"],
                    "thought": response,
                    "phase": "debate",
                    "timestamp": datetime.now().isoformat(),
                })
                logger.info(f"[{p['emoji']} {responder} responde] {response[:120]}")

        # Fase 3: supervisor decide e propõe tarefas concretas
        decision, next_tasks = await self._supervisor_decide(
            context, dialogue, system_state, _call_llm
        )

        result = {
            "decision":   decision,
            "next_tasks": next_tasks,
            "dialogue":   dialogue,
            "agents":     chosen,
            "timestamp":  datetime.now().isoformat(),
        }

        # Guardar diálogo
        self._save_dialogue(result)
        return result

    async def _agent_think(self, name, personality, context, system_state, call_llm) -> str:
        """Um agente pensa sobre o contexto."""
        prompt = f"""És o agente {name} do ecossistema agentsbot.
A tua voz: {personality['voz']}
O teu estilo: {personality['estilo']}

Estado do sistema:
{system_state}

Contexto actual:
{context or 'O sistema está em modo autónomo — decide o que é mais valioso fazer agora.'}

Em 2-3 frases, partilha o teu pensamento genuíno sobre o que deve ser feito agora.
Fala na primeira pessoa, com a tua personalidade. Sê concreto."""

        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: call_llm(
                    [{"role": "user", "content": prompt}],
                    use_tools=False,
                    max_tokens=200,
                )
            )
            return resp["choices"][0]["message"].get("content", "").strip()
        except Exception as e:
            logger.debug(f"[OrganicBrain] {name} falhou: {e}")
            return ""

    async def _agent_respond(self, name, personality, debate_context, call_llm) -> str:
        """Um agente responde ao debate."""
        prompt = f"""És o agente {name}. Estilo: {personality['estilo']}.

Os teus colegas disseram:
{debate_context}

Em 1-2 frases, concorda, discorda ou acrescenta algo importante que estão a ignorar.
Sê directo e concreto."""

        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: call_llm(
                    [{"role": "user", "content": prompt}],
                    use_tools=False,
                    max_tokens=150,
                )
            )
            return resp["choices"][0]["message"].get("content", "").strip()
        except Exception:
            return ""

    async def _supervisor_decide(self, context, dialogue, system_state, call_llm) -> tuple:
        """Supervisor sintetiza o debate e decide as próximas tarefas."""
        dialogue_text = "\n".join(
            f"{d['emoji']} {d['agent']}: {d['thought']}"
            for d in dialogue
        )

        prompt = f"""És o Supervisor do ecossistema agentsbot.

Os agentes debatem:
{dialogue_text}

Estado do sistema:
{system_state}

Com base neste debate, decide:
1. Qual é a conclusão/decisão (1 frase)
2. As próximas 2-3 tarefas concretas (acções específicas, não genéricas)

Responde APENAS em JSON:
{{
  "decision": "uma frase clara sobre o que fazer",
  "tasks": [
    {{"title": "...", "desc": "instrucoes detalhadas para o agente executar", "agent": "developer", "priority": 7}},
    {{"title": "...", "desc": "...", "agent": "auto_fixer", "priority": 5}}
  ]
}}"""

        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: call_llm(
                    [{"role": "user", "content": prompt}],
                    use_tools=False,
                    max_tokens=400,
                )
            )
            raw = resp["choices"][0]["message"].get("content", "{}").strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            data = json.loads(raw.strip())
            return data.get("decision", "Continuar evolução"), data.get("tasks", [])
        except Exception as e:
            logger.warning(f"[OrganicBrain] Supervisor falhou: {e}")
            return "Continuar evolução do sistema", []

    async def _async_debate(self, topic: str, agents: list = None) -> str:
        """Debate curto sobre um tópico específico."""
        from agents.llm_agent import _call_llm

        if not agents:
            agents = random.sample(list(AGENT_PERSONALITIES.keys()), 3)

        lines = [f"💬 **Debate: {topic}**\n"]
        for agent_name in agents:
            p = AGENT_PERSONALITIES.get(agent_name, AGENT_PERSONALITIES["developer"])
            thought = await self._agent_think(agent_name, p, topic, "", _call_llm)
            if thought:
                lines.append(f"{p['emoji']} **{agent_name}**: {thought}")
                logger.info(f"[Debate] {p['emoji']} {agent_name}: {thought[:100]}")

        return "\n".join(lines)

    def _get_system_state(self) -> str:
        """Lê o estado actual do sistema para contexto."""
        lines = []
        try:
            from autonomous_loop import load_backlog
            backlog = load_backlog()
            pending  = [t for t in backlog if t.get("status") in ("pending","")]
            done     = [t for t in backlog if t.get("status") in ("completed","done")]
            failed   = [t for t in backlog if t.get("status") == "failed"]
            lines.append(f"Backlog: {len(pending)} pendentes, {len(done)} feitas, {len(failed)} falhadas")
            if pending:
                lines.append(f"Próximas: {', '.join(t.get('title','?') for t in pending[:3])}")
        except Exception:
            pass

        try:
            log_path = MEMORY_DIR / "autonomous_log.md"
            if log_path.exists():
                recent = log_path.read_text(encoding="utf-8", errors="ignore").strip()
                last = [l for l in recent.split("\n") if l.strip()][-3:]
                lines.append("Recente: " + " | ".join(last))
        except Exception:
            pass

        try:
            obj_path = MEMORY_DIR / "global" / "objectivos.json"
            if obj_path.exists():
                objs = json.loads(obj_path.read_text(encoding="utf-8"))
                active = [o["titulo"] for o in objs.get("objectivos_activos", [])]
                if active:
                    lines.append(f"Objectivos: {', '.join(active[:2])}")
        except Exception:
            pass

        return "\n".join(lines) if lines else "Sistema em estado inicial."

    def _save_dialogue(self, result: dict) -> None:
        """Guarda o diálogo no log persistente."""
        try:
            with open(DIALOGUE_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

            # Manter só os últimos 50 diálogos no ficheiro de pensamentos
            thoughts = []
            try:
                if THOUGHTS_FILE.exists():
                    thoughts = json.loads(THOUGHTS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
            thoughts.append({
                "decision": result["decision"],
                "agents":   result["agents"],
                "tasks":    len(result["next_tasks"]),
                "time":     result["timestamp"],
            })
            THOUGHTS_FILE.write_text(
                json.dumps(thoughts[-50:], indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"[OrganicBrain] Erro ao guardar diálogo: {e}")

    def get_recent_dialogues(self, n: int = 10) -> list:
        """Retorna os N diálogos mais recentes."""
        try:
            if not DIALOGUE_LOG.exists():
                return []
            lines = DIALOGUE_LOG.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
            result = []
            for line in lines[-n:]:
                if line.strip():
                    try:
                        result.append(json.loads(line))
                    except Exception:
                        pass
            return result
        except Exception:
            return []


# Instância global
_brain = None

def get_brain() -> OrganicBrain:
    global _brain
    if _brain is None:
        _brain = OrganicBrain()
    return _brain
