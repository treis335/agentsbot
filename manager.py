import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable, Optional

from executor import run_agent_task

logger = logging.getLogger(__name__)

AGENTS_FILE = Path("agents.json")
MEMORY_DIR = Path("memory/agents")

@dataclass
class Agent:
    id: str
    name: str
    system_prompt: str
    model: str = "deepseek-chat"
    status: str = "idle"
    context: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    _task: Optional[asyncio.Task] = field(default=None, repr=False, compare=False)
    _stop: Optional[asyncio.Event] = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "system_prompt": self.system_prompt, "model": self.model,
            "status": "idle", "context": [], "metadata": self.metadata,
        }

class AgentManager:
    def __init__(self, api_key: str, interval: int = 300):
        self.agents: dict[str, Agent] = {}
        self.api_key = api_key
        self.interval = interval
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if not AGENTS_FILE.exists():
            return
        try:
            for d in json.loads(AGENTS_FILE.read_text(encoding="utf-8")):
                a = Agent(**{k: v for k, v in d.items() if not k.startswith("_")})
                a.status = "idle"
                mem = MEMORY_DIR / f"{a.id}.json"
                if mem.exists():
                    a.context = json.loads(mem.read_text(encoding="utf-8"))
                self.agents[a.id] = a
            logger.info(f"[Manager] {len(self.agents)} agente(s) carregado(s).")
        except Exception as e:
            logger.error(f"[Manager] Erro ao carregar: {e}")

    def _save(self):
        AGENTS_FILE.write_text(
            json.dumps([a.to_dict() for a in self.agents.values()], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _save_memory(self, agent: Agent):
        path = MEMORY_DIR / f"{agent.id}.json"
        ctx = agent.context[-40:] if len(agent.context) > 40 else agent.context
        path.write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_agent(self, name: str, mission: str, model: str = "deepseek-chat") -> Agent:
        a = Agent(id=str(uuid.uuid4()), name=name, system_prompt=mission, model=model)
        self.agents[a.id] = a
        self._save()
        logger.info(f"[Manager] Agente criado: {name}")
        return a

    def delete_agent(self, agent_id: str) -> bool:
        a = self._get(agent_id)
        if not a:
            return False
        self.stop_agent(a.id)
        del self.agents[a.id]
        self._save()
        mem = MEMORY_DIR / f"{a.id}.json"
        mem.unlink(missing_ok=True)
        return True

    def list_agents(self) -> list[Agent]:
        return list(self.agents.values())

    def _get(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id) or next(
            (a for a in self.agents.values() if a.id.startswith(agent_id)), None
        )

    async def start_agent(self, agent_id: str, chat_id: int, send_fn: Callable) -> bool:
        a = self._get(agent_id)
        if not a or a.status == "running":
            return False
        a._stop = asyncio.Event()
        a.status = "running"
        self._save()
        a._task = asyncio.create_task(self._agent_loop(a, chat_id, send_fn))
        return True

    def stop_agent(self, agent_id: str):
        a = self._get(agent_id)
        if not a:
            return
        if a._stop:
            a._stop.set()
        if a._task and not a._task.done():
            a._task.cancel()
        a.status = "stopped"
        self._save()

    async def _agent_loop(self, agent: Agent, chat_id: int, send_fn: Callable):
        await send_fn(chat_id=chat_id, text=f"[VERDE] **{agent.name}** iniciado em modo aut?nomo.", parse_mode="Markdown")
        while not agent._stop.is_set():
            try:
                await send_fn(chat_id=chat_id, text=f"[ENG] **{agent.name}** a executar ciclo...", parse_mode="Markdown")
                auto_task = (
                    "Executa o teu ciclo autónomo. Analisa o repositório usando as ferramentas disponíveis, "
                    "identifica o que pode ser melhorado ou criado, faz as alterações necessárias diretamente "
                    "(escreve ficheiros, executa código, faz commit), e reporta o que fizeste."
                )
                async def notify(tool_name: str, args: dict, result: str):
                    preview = str(result)[:300]
                    await send_fn(chat_id=chat_id, text=f"[FIX] `{tool_name}` -> {preview}", parse_mode="Markdown")
                final, agent.context = await run_agent_task(
                    system_prompt=agent.system_prompt,
                    task=auto_task,
                    api_key=self.api_key,
                    model=agent.model,
                    on_tool_call=notify,
                    context=agent.context if agent.context else None,
                )
                self._save_memory(agent)
                await send_fn(chat_id=chat_id, text=f"[OK] **{agent.name}** concluiu:\n{final[:4000]}", parse_mode="Markdown")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{agent.name}] Erro: {e}", exc_info=True)
                await send_fn(chat_id=chat_id, text=f"[!] **{agent.name}** erro: {e}")
            try:
                await asyncio.wait_for(agent._stop.wait(), timeout=self.interval)
                break
            except asyncio.TimeoutError:
                pass
        agent.status = "stopped"
        self._save()
        await send_fn(chat_id=chat_id, text=f"[VERM] **{agent.name}** parado.", parse_mode="Markdown")

    async def run_task(self, agent_id: str, task: str, on_tool_call: Callable | None = None) -> str:
        a = self._get(agent_id)
        if not a:
            return "Agente não encontrado."
        final, a.context = await run_agent_task(
            system_prompt=a.system_prompt,
            task=task,
            api_key=self.api_key,
            model=a.model,
            on_tool_call=on_tool_call,
            context=a.context if a.context else None,
        )
        self._save_memory(a)
        return final