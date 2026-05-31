"""
agents/collaboration/brainstorm_session.py — Sessão de brainstorming colaborativo.

Um ciclo completo de colaboração entre agentes:

  Fase 1 — GERAÇÃO (brainstormer_auto)
    Gera 3-5 ideias sobre um tema (rotativo ou detectado dos logs)

  Fase 2 — CRÍTICA (arquiteto + developer)
    Cada agente lê as ideias e dá feedback: o que é viável, o que é risco

  Fase 3 — SÍNTESE (supervisor)
    Combina o feedback e selecciona a melhor ideia

  Fase 4 — IMPLEMENTAÇÃO
    Adiciona tarefa ao backlog com contexto completo da discussão

  Fase 5 — PARTILHA DE CONHECIMENTO
    Qualquer agente pode partilhar descobertas durante execução

Corre autonomamente a cada N ciclos do loop principal.
Resultado publicado no bus + notificação Telegram com resumo.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from agents.collaboration.agent_bus import get_agent_bus, MsgType
from core.config import Config

logger = logging.getLogger(__name__)

_SESSION_LOG = Path("memory") / "brainstorm_sessions.json"

# Temas rotativos para brainstorming autónomo
BRAINSTORM_THEMES = [
    "Como tornar os agentes mais eficientes e rápidos?",
    "Que novas capacidades podem ser adicionadas ao ecossistema?",
    "Como melhorar a qualidade das respostas dos agentes?",
    "Que integrações externas seriam mais valiosas?",
    "Como optimizar o uso de tokens e reduzir custos?",
    "Que padrões de erro se repetem e como preveni-los?",
    "Como melhorar a experiência de uso via Telegram?",
    "Que dados/métricas faltam para tomar melhores decisões?",
    "Como tornar o self-improvement mais seguro e eficaz?",
    "Que agentes especializados ainda fazem falta no ecossistema?",
]


class BrainstormSession:
    """Sessão de brainstorming colaborativo multi-agente."""

    def __init__(self, theme: str = "", telegram_bot=None, owner_id: int = 0):
        self.theme = theme or self._pick_theme()
        self.telegram_bot = telegram_bot
        self.owner_id = owner_id
        self.bus = get_agent_bus()
        self.topic = f"brainstorm_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.ideas: list[str] = []
        self.critiques: list[dict] = []
        self.final_idea: str = ""

    def _pick_theme(self) -> str:
        """Escolhe tema baseado no que falhou mais recentemente."""
        try:
            eps_file = Path("memory/loop_episodes.json")
            if eps_file.exists():
                eps = json.loads(eps_file.read_text(encoding="utf-8"))
                failed = [e for e in eps if not e.get("success")][-5:]
                if failed:
                    # Usar falha mais comum como tema
                    themes_from_failures = [e.get("task_desc", "")[:80] for e in failed]
                    if themes_from_failures:
                        return f"Como resolver problemas como: '{themes_from_failures[0]}'?"
        except Exception:
            pass
        # Tema rotativo por hora do dia
        hour = datetime.now().hour
        return BRAINSTORM_THEMES[hour % len(BRAINSTORM_THEMES)]

    async def run(self) -> dict:
        """Executa sessão completa. Retorna sumário."""
        logger.info(f"[Brainstorm] Sessão iniciada: {self.theme[:60]}")

        # Fase 1: Geração de ideias
        await self._phase_generate()
        if not self.ideas:
            return {"status": "failed", "reason": "Sem ideias geradas"}

        # Fase 2: Crítica e debate
        await self._phase_critique()

        # Fase 3: Síntese
        await self._phase_synthesize()

        # Fase 4: Adicionar ao backlog
        task_id = self._add_to_backlog()

        # Fase 5: Partilhar conhecimento geral
        await self._phase_knowledge_share()

        # Guardar sessão
        result = {
            "topic": self.topic,
            "theme": self.theme,
            "timestamp": datetime.now().isoformat(),
            "ideas_generated": len(self.ideas),
            "critiques_received": len(self.critiques),
            "final_idea": self.final_idea[:200],
            "task_created": task_id,
        }
        self._save_session(result)

        # Notificar
        await self._notify(result)

        logger.info(f"[Brainstorm] Sessão concluída: {self.final_idea[:60]}")
        return result

    # ── Fases ─────────────────────────────────────────────────────────────────

    async def _phase_generate(self) -> None:
        """Fase 1: brainstormer gera 3 ideias."""
        prompt = (
            f"TEMA DE BRAINSTORMING: {self.theme}\n\n"
            "Gera 3 ideias concretas e implementáveis para este tema. "
            "Cada ideia deve ter: nome curto, descrição em 1 frase, impacto esperado.\n\n"
            "Responde em JSON:\n"
            '[{"nome":"...","descricao":"...","impacto":"..."},...]\n\n'
            "Só JSON, sem texto extra."
        )
        response = await self._call_agent("brainstormer_auto", prompt)

        try:
            import re
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                ideas_raw = json.loads(match.group())
                self.ideas = [
                    f"{i.get('nome','?')}: {i.get('descricao','?')} (impacto: {i.get('impacto','?')})"
                    for i in ideas_raw
                ]
        except Exception:
            # Fallback: tratar resposta como lista de ideias em texto
            lines = [l.strip() for l in response.splitlines() if l.strip() and len(l) > 20]
            self.ideas = lines[:3]

        # Publicar ideias no bus
        for idea in self.ideas:
            self.bus.send(
                sender="brainstormer_auto",
                msg_type=MsgType.IDEA,
                content=idea,
                topic=self.topic,
            )
        logger.info(f"[Brainstorm] {len(self.ideas)} ideias geradas")

    async def _phase_critique(self) -> None:
        """Fase 2: arquiteto e developer criticam as ideias."""
        ideas_text = "\n".join(f"  {i+1}. {idea}" for i, idea in enumerate(self.ideas))
        critics = [
            ("arquiteto",  "Do ponto de vista de arquitectura e escalabilidade,"),
            ("developer",  "Do ponto de vista de implementação e esforço técnico,"),
        ]

        for agent_name, perspective in critics:
            prompt = (
                f"IDEIAS PARA DISCUSSÃO:\n{ideas_text}\n\n"
                f"TEMA: {self.theme}\n\n"
                f"{perspective} analisa cada ideia e diz:\n"
                "- Qual a melhor e porquê\n"
                "- Qual o maior risco\n"
                "- Que melhoria sugeres à melhor ideia\n\n"
                "Sê directo e concreto. Máximo 4 frases."
            )
            critique = await self._call_agent(agent_name, prompt)
            self.critiques.append({"agent": agent_name, "critique": critique})

            # Publicar crítica no bus
            self.bus.send(
                sender=agent_name,
                msg_type=MsgType.CRITIQUE,
                content=critique[:300],
                topic=self.topic,
            )
            logger.info(f"[Brainstorm] Crítica de {agent_name} recebida")

    async def _phase_synthesize(self) -> None:
        """Fase 3: supervisor sintetiza e escolhe."""
        ideas_text = "\n".join(f"  {i+1}. {idea}" for i, idea in enumerate(self.ideas))
        critiques_text = "\n".join(
            f"  {c['agent']}: {c['critique'][:150]}" for c in self.critiques
        )

        prompt = (
            f"TEMA: {self.theme}\n\n"
            f"IDEIAS PROPOSTAS:\n{ideas_text}\n\n"
            f"FEEDBACK DA EQUIPA:\n{critiques_text}\n\n"
            "Como Supervisor, sintetiza o debate e decide:\n"
            "1. Qual ideia implementar (combina o melhor de cada uma se fizer sentido)\n"
            "2. Como implementá-la em termos concretos (2-3 passos)\n"
            "3. Qual agente deve liderar a implementação\n\n"
            "Sê decisivo e concreto. Máximo 5 frases."
        )
        self.final_idea = await self._call_agent("supervisor", prompt)

        self.bus.send(
            sender="supervisor",
            msg_type=MsgType.CONSENSUS,
            content=self.final_idea[:400],
            topic=self.topic,
        )

    async def _phase_knowledge_share(self) -> None:
        """Fase 5: agentes partilham conhecimento relevante que descobriram."""
        try:
            eps_file = Path("memory/loop_episodes.json")
            if not eps_file.exists():
                return
            eps = json.loads(eps_file.read_text(encoding="utf-8"))
            recent_success = [e for e in eps[-20:] if e.get("success")][-3:]

            for ep in recent_success:
                knowledge = (
                    f"Aprendi que '{ep.get('task_desc','?')[:60]}' "
                    f"funciona bem com o agente {ep.get('agent','?')}."
                )
                self.bus.send(
                    sender=ep.get("agent", "sistema"),
                    msg_type=MsgType.KNOWLEDGE,
                    content=knowledge,
                    topic="knowledge_base",
                )
        except Exception as e:
            logger.debug(f"[Brainstorm] Knowledge share falhou: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _call_agent(self, agent_name: str, prompt: str) -> str:
        """Chama um agente com um prompt e retorna a resposta."""
        try:
            from agents.llm_agent import LLMAgent
            agent = LLMAgent(agent_name=agent_name)
            return await agent.chat(user_id=0, user_message=prompt)
        except Exception as e:
            logger.warning(f"[Brainstorm] {agent_name} falhou: {e}")
            return f"[{agent_name} indisponível: {e}]"

    def _add_to_backlog(self) -> str:
        """Adiciona a ideia final ao backlog como tarefa."""
        import uuid
        task_id = f"brainstorm_{uuid.uuid4().hex[:8]}"
        try:
            bl_path = Path("memory/backlog.json")
            bl = json.loads(bl_path.read_text(encoding="utf-8")) if bl_path.exists() else []
            bl = bl if isinstance(bl, list) else []

            task = {
                "id": task_id,
                "title": f"[Brainstorm] {self.theme[:50]}",
                "desc": (
                    f"Ideia gerada em sessão colaborativa:\n\n{self.final_idea}\n\n"
                    f"Debate completo em memory/brainstorm_sessions.json (topic: {self.topic})"
                ),
                "status": "pending",
                "priority": 7,
                "source": "brainstorm_session",
                "created_at": datetime.now().isoformat(),
            }
            bl.append(task)
            bl_path.write_text(json.dumps(bl, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"[Brainstorm] Tarefa adicionada: {task_id}")
        except Exception as e:
            logger.warning(f"[Brainstorm] Falha ao adicionar backlog: {e}")
        return task_id

    def _save_session(self, result: dict) -> None:
        try:
            sessions = []
            if _SESSION_LOG.exists():
                sessions = json.loads(_SESSION_LOG.read_text(encoding="utf-8"))
            sessions.append(result)
            sessions = sessions[-50:]  # manter últimas 50
            _SESSION_LOG.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    async def _notify(self, result: dict) -> None:
        if not self.telegram_bot or not self.owner_id:
            return
        try:
            ideas_list = "\n".join(f"  {i+1}. {idea[:60]}" for i, idea in enumerate(self.ideas))
            msg = (
                f"🧠 *Sessão de Brainstorming*\n\n"
                f"*Tema:* {self.theme[:80]}\n\n"
                f"*Ideias geradas:*\n{ideas_list}\n\n"
                f"*Decisão da equipa:*\n_{self.final_idea[:200]}_\n\n"
                f"✅ Tarefa adicionada ao backlog para implementação."
            )
            await self.telegram_bot.send_message(
                chat_id=self.owner_id,
                text=msg,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.debug(f"[Brainstorm] Notificação falhou: {e}")
