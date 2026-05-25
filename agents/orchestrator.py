"""
agents/orchestrator.py — Orquestrador de agentes.

Coordena a equipa de agentes:
- Escolhe o agente certo para cada tarefa
- Distribui trabalho
- Monitoriza execucao
- Recolhe resultados
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from core.config import Config
from core.bus import bus
from .manager import AgentManager
from .executor import AgentExecutor
from .models import Agent, AgentStatus

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orquestrador que coordena a equipa de agentes.

    Uso:
        orch = AgentOrchestrator()
        resultado = await orch.delegate("Implementa uma funcao de login", "developer")
        resultado = await orch.execute_pipeline("Dev Cycle")
    """

    def __init__(self):
        self.config = Config
        self.manager = AgentManager()
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def delegate(self, task: str, agent_name: str = "",
                       context: Optional[list] = None,
                       on_tool_call=None) -> str:
        """
        Delega uma tarefa a um agente especifico ou ao mais adequado.

        Args:
            task: Descricao da tarefa
            agent_name: Nome do agente (vazio = supervisor decide)
            context: Contexto anterior
            on_tool_call: Callback para notificacoes

        Returns:
            Resultado da execucao
        """
        # Se nao foi especificado agente, usar supervisor para decidir
        if not agent_name:
            agent_name = await self._decide_agent(task)

        logger.info(f"[Orchestrator] A delegar para '{agent_name}': {task[:100]}...")

        # Criar executor
        executor = AgentExecutor(agent_name)

        # Atualizar status do agente
        agent = self._find_agent(agent_name)
        if agent:
            self.manager.update_status(agent.id, AgentStatus.RUNNING)

        try:
            # Executar
            result, context = await executor.run(
                task=task,
                context=context,
                on_tool_call=on_tool_call,
            )

            # Atualizar status
            if agent:
                self.manager.update_status(agent.id, AgentStatus.IDLE)

            # Publicar evento
            await bus.publish("task.completed", {
                "agent": agent_name,
                "task": task[:100],
                "result": result[:500],
            })

            return result

        except Exception as e:
            logger.error(f"[Orchestrator] Erro no agente {agent_name}: {e}")
            if agent:
                self.manager.update_status(agent.id, AgentStatus.ERROR)
            return f"Erro: {e}"

    async def _decide_agent(self, task: str) -> str:
        """
        Decide qual o melhor agente para uma tarefa.

        Usa palavras-chave para fazer o match inicial.
        """
        task_lower = task.lower()

        # Mapeamento de palavras-chave para agentes
        keywords = {
            "supervisor": ["coordenar", "delegar", "gerir", "organizar", "planejar"],
            "developer": ["implementar", "codigo", "programar", "funcao", "classe",
                         "modulo", "api", "endpoint", "script", "algoritmo"],
            "arquiteto": ["arquitetura", "estrutura", "desenhar", "padrao", "design",
                         "escalabilidade", "SOLID", "refatorar_estrutura"],
            "qa_tester": ["testar", "teste", "qualidade", "validar", "cobertura",
                         "unitario", "integracao", "bug", "regressao"],
            "explorador": ["pesquisar", "explorar", "investigar", "nova_tecnologia",
                          "biblioteca", "tendencia", "github", "descobrir"],
            "documentador": ["documentar", "readme", "docs", "changelog", "guia",
                            "tutorial", "markdown", "wiki"],
            "code_reviewer": ["revisar", "review", "auditar", "inspecionar",
                             "qualidade_codigo", "padroes"],
            "auto_fixer": ["corrigir", "bug", "erro", "falha", "problema",
                          "consertar", "reparar", "hotfix"],
            "auto_optimizer": ["otimizar", "performance", "velocidade", "eficiencia",
                              "refatorar", "melhorar", "acelerar"],
            "devops": ["devops", "deploy", "ci_cd", "dependencia", "ambiente",
                      "infraestrutura", "docker", "configuracao"],
            "aprendiz": ["aprender", "estudar", "analisar", "padrao", "tendencia",
                        "evoluir", "melhoria_continua"],
        }

        # Calcular score para cada agente
        scores = {}
        for agent, words in keywords.items():
            score = sum(1 for word in words if word in task_lower)
            if score > 0:
                scores[agent] = score

        if scores:
            best = max(scores, key=scores.get)
            logger.info(f"[Orchestrator] Agente escolhido: {best} (score={scores[best]})")
            return best

        # Fallback para developer
        logger.info("[Orchestrator] Nenhum agente especifico, fallback para developer")
        return "developer"

    def _find_agent(self, name: str) -> Optional[Agent]:
        """Encontra um agente pelo nome."""
        for agent in self.manager.list_agents():
            if agent.name == name:
                return agent
        return None

    async def run_autonomous_cycle(self, on_tool_call=None) -> dict:
        """
        Executa um ciclo autonomo completo.

        O supervisor decide o que fazer, delega, e recolhe resultados.
        """
        logger.info("[Orchestrator] Ciclo autonomo iniciado")

        # 1. Supervisor analisa o estado do sistema
        analysis_task = (
            "Analisa o estado atual do sistema. Le os ficheiros principais, "
            "verifica o git status, ve as metricas, e decide o que precisa ser feito. "
            "Identifica 1-3 acoes prioritarias e delega-as aos agentes corretos."
        )

        result = await self.delegate(analysis_task, "supervisor", on_tool_call=on_tool_call)

        return {
            "cycle_time": datetime.now().isoformat(),
            "result": result,
        }
