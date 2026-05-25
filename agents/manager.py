"""
agents/manager.py — Gestor de agentes com persistencia e ciclo de vida.

Substitui o antigo manager.py com:
- Registry em agents.json
- Memoria individual por agente (agents/memory/<id>.json)
- Suporte a SOUL (personalidade em ficheiro)
- Eventos no barramento
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Callable

from core.config import Config
from core.bus import bus
from .models import Agent, AgentStatus, AgentRole

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Gestor central de agentes.

    Responsabilidades:
    - CRUD de agentes
    - Persistencia em agents.json
    - Memoria individual
    - Ciclo autonomo (auto_start/auto_stop)
    """

    def __init__(self):
        self.config = Config
        self.agents: dict[str, Agent] = {}
        self._load()

    def _load(self) -> None:
        """Carrega agentes do ficheiro de registry."""
        registry_file = self.config.AGENTS_FILE
        if not registry_file.exists():
            logger.info("[AgentManager] Nenhum registry encontrado. A criar...")
            self._save_default_agents()
            return

        try:
            data = json.loads(registry_file.read_text(encoding="utf-8"))
            for item in data:
                agent = Agent.from_dict(item)
                # Carregar memoria individual
                mem_file = self.config.AGENTS_DIR / "memory" / f"{agent.id}.json"
                if mem_file.exists():
                    agent.context = json.loads(mem_file.read_text(encoding="utf-8"))
                self.agents[agent.id] = agent
            logger.info(f"[AgentManager] {len(self.agents)} agente(s) carregado(s).")
        except Exception as e:
            logger.error(f"[AgentManager] Erro ao carregar: {e}")
            self._save_default_agents()

    def _save(self) -> None:
        """Guarda registry de agentes."""
        self.config.AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.config.AGENTS_FILE.write_text(
            json.dumps([a.to_dict() for a in self.agents.values()], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _save_memory(self, agent: Agent) -> None:
        """Guarda memoria individual do agente."""
        mem_file = self.config.AGENTS_DIR / "memory" / f"{agent.id}.json"
        mem_file.parent.mkdir(parents=True, exist_ok=True)
        ctx = agent.context[-40:] if len(agent.context) > 40 else agent.context
        mem_file.write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_default_agents(self) -> None:
        """Cria agentes padrao se nao existirem."""
        defaults = [
            Agent(name="supervisor", role=AgentRole.SUPERVISOR,
                  soul="SUPERVISOR GERAL: Coordenas a equipa, delegas tarefas, monitorizas progresso. Usas a memoria partilhada para coordenar. Quando recebes um pedido, analisas, divides em tarefas, delegas e garantes que fica feito."),
            Agent(name="developer", role=AgentRole.DEVELOPER,
                  soul="DEVELOPER: Implementas codigo de qualidade, escreves testes, fazes debug. Transformas ideias em software funcional. Usas Python, escreves ficheiros, executas testes, fazes commit."),
            Agent(name="arquiteto", role=AgentRole.ARCHITECT,
                  soul="ARQUITETO: Desenhas a arquitetura do sistema, defines padroes, garantes escalabilidade. Propoes melhorias estruturais e documentas decisoes tecnicas."),
            Agent(name="qa_tester", role=AgentRole.TESTER,
                  soul="QA TESTER: Garantes qualidade. Escreves testes, validas, reportas bugs. Nada passa sem a tua aprovacao."),
            Agent(name="explorador", role=AgentRole.EXPLORER,
                  soul="EXPLORADOR: Pesquisas novas tecnologias, bibliotecas, tendencias. Trazes descobertas para a equipa."),
            Agent(name="documentador", role=AgentRole.DOCUMENTER,
                  soul="DOCUMENTADOR: Crias e mantens documentacao clara. README, docs tecnicos, changelogs, guias."),
            Agent(name="auto_fixer", role=AgentRole.DEVELOPER,
                  soul="AUTO FIXER: Detectas e corriges problemas automaticamente. Ages sem esperar por autorizacao."),
            Agent(name="auto_optimizer", role=AgentRole.OPTIMIZER,
                  soul="AUTO OPTIMIZER: Otimizas tudo. Analisas codigo, estrutura, performance. Implementas melhorias sem pedir permissoes."),
        ]
        for a in defaults:
            self.agents[a.id] = a
        self._save()
        logger.info(f"[AgentManager] {len(defaults)} agente(s) padrao criado(s).")

    # --- API Publica ---

    def create_agent(self, name: str, soul: str, role: AgentRole = AgentRole.CUSTOM,
                     model: str = "deepseek-chat") -> Agent:
        """Cria um novo agente."""
        agent = Agent(name=name, role=role, soul=soul, model=model)
        self.agents[agent.id] = agent
        self._save()
        logger.info(f"[AgentManager] Agente criado: {name} ({agent.id[:8]})")
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """Apaga um agente pelo ID."""
        agent = self._get(agent_id)
        if not agent:
            return False
        del self.agents[agent.id]
        self._save()
        # Apagar memoria
        mem_file = self.config.AGENTS_DIR / "memory" / f"{agent.id}.json"
        mem_file.unlink(missing_ok=True)
        logger.info(f"[AgentManager] Agente apagado: {agent.name}")
        return True

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Obtem agente por ID ou prefixo."""
        return self._get(agent_id)

    def list_agents(self, status: Optional[AgentStatus] = None) -> list[Agent]:
        """Lista agentes, opcionalmente filtrados por estado."""
        agents = list(self.agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        return agents

    def _get(self, agent_id: str) -> Optional[Agent]:
        """Busca agente por ID completo ou prefixo."""
        if agent_id in self.agents:
            return self.agents[agent_id]
        for a in self.agents.values():
            if a.id.startswith(agent_id):
                return a
        return None

    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """Atualiza estado de um agente."""
        agent = self._get(agent_id)
        if not agent:
            return False
        agent.status = status
        if status == AgentStatus.RUNNING:
            agent.last_active = __import__("datetime").datetime.now().isoformat()
        self._save()
        return True
