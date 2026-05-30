"""
pipelines/state_machine.py — Máquina de estados leve para workflows deterministas.

Implementação própria, sem LangGraph nem dependências externas.
Cada workflow é um grafo de estados com transições definidas.
Guarda estado em ficheiro para sobreviver a restarts.

Uso:
    sm = StateMachine.from_yaml("dev_cycle")
    run_id = sm.start(context={"task": "Fix login bug"})
    state = sm.tick(run_id)   # avança um passo
    state = sm.get_state(run_id)
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

import yaml

from core.config import Config

logger = logging.getLogger(__name__)


# ─── ENUMS ─────────────────────────────────────────────────────────────────────

class StepState(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class RunState(str, Enum):
    CREATED   = "created"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    PAUSED    = "paused"


# ─── MODELOS ───────────────────────────────────────────────────────────────────

@dataclass
class StepDefinition:
    """Definição estática de um passo (vem do YAML)."""
    id: str
    name: str
    agent_role: str
    task_template: str
    on_success: str = "next"   # "next" | id-de-passo | "end"
    on_failure: str = "fail"   # "fail" | "retry" | id-de-passo
    max_retries: int = 1
    condition: str = ""        # expressão Python simples avaliada com eval()


@dataclass
class StepRun:
    """Estado de execução de um passo numa run específica."""
    step_id: str
    state: StepState = StepState.PENDING
    attempts: int = 0
    result: str = ""
    task_id: str = ""
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "StepRun":
        d["state"] = StepState(d["state"])
        return cls(**d)


@dataclass
class WorkflowRun:
    """Uma instância de execução de um workflow."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    workflow_name: str = ""
    state: RunState = RunState.CREATED
    current_step_id: str = ""
    context: dict = field(default_factory=dict)
    steps: dict[str, StepRun] = field(default_factory=dict)  # step_id → StepRun
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "state": self.state.value,
            "current_step_id": self.current_step_id,
            "context": self.context,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowRun":
        steps = {k: StepRun.from_dict(v) for k, v in d.get("steps", {}).items()}
        return cls(
            run_id=d["run_id"],
            workflow_name=d["workflow_name"],
            state=RunState(d["state"]),
            current_step_id=d.get("current_step_id", ""),
            context=d.get("context", {}),
            steps=steps,
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            error=d.get("error", ""),
        )


# ─── WORKFLOW DEFINITION ───────────────────────────────────────────────────────

@dataclass
class WorkflowDefinition:
    """Definição estática carregada do YAML."""
    name: str
    description: str
    version: str
    initial_step: str
    steps: dict[str, StepDefinition]  # step_id → StepDefinition


# ─── STATE MACHINE ─────────────────────────────────────────────────────────────

class StateMachine:
    """
    Máquina de estados leve para workflows multi-agente.

    Não usa LangGraph — implementação Python pura com persistência em JSONL.
    """

    TEMPLATES_DIR = Config.PIPELINES_DIR / "workflow_templates"
    RUNS_DIR = Config.PIPELINES_DIR / "runs"

    def __init__(self, definition: WorkflowDefinition):
        self.definition = definition
        self.RUNS_DIR.mkdir(parents=True, exist_ok=True)
        # Hook opcional: chamado quando um passo precisa de ser executado
        self._step_executor: Optional[Callable] = None

    # ── Carregamento ────────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, workflow_name: str) -> "StateMachine":
        """Carrega workflow de YAML. Ex: StateMachine.from_yaml('dev_cycle')"""
        path = cls.TEMPLATES_DIR / f"{workflow_name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Workflow não encontrado: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        steps = {}
        for s in raw.get("steps", []):
            steps[s["id"]] = StepDefinition(
                id=s["id"],
                name=s["name"],
                agent_role=s.get("agent_role", "developer"),
                task_template=s.get("task_template", ""),
                on_success=s.get("on_success", "next"),
                on_failure=s.get("on_failure", "fail"),
                max_retries=s.get("max_retries", 1),
                condition=s.get("condition", ""),
            )

        definition = WorkflowDefinition(
            name=raw["name"],
            description=raw.get("description", ""),
            version=raw.get("version", "1.0"),
            initial_step=raw["initial_step"],
            steps=steps,
        )
        logger.info(f"[StateMachine] Workflow carregado: {workflow_name} ({len(steps)} passos)")
        return cls(definition)

    def set_executor(self, executor: Callable) -> None:
        """Define o callable que executa cada passo. Assinatura: executor(step_def, run) → str"""
        self._step_executor = executor

    # ── Ciclo de vida ───────────────────────────────────────────────────────────

    def start(self, context: Optional[dict] = None) -> str:
        """Cria uma nova run e retorna o run_id."""
        step_runs = {
            sid: StepRun(step_id=sid)
            for sid in self.definition.steps
        }
        run = WorkflowRun(
            workflow_name=self.definition.name,
            state=RunState.CREATED,
            current_step_id=self.definition.initial_step,
            context=context or {},
            steps=step_runs,
        )
        self._save_run(run)
        logger.info(f"[StateMachine] Run iniciada: {run.run_id} ({self.definition.name})")
        return run.run_id

    def tick(self, run_id: str) -> WorkflowRun:
        """
        Avança a run um passo.
        Se o step_executor estiver definido, executa o passo.
        Retorna o estado atualizado da run.
        """
        run = self._load_run(run_id)
        if not run:
            raise ValueError(f"Run não encontrada: {run_id}")

        if run.state in (RunState.COMPLETED, RunState.FAILED):
            logger.warning(f"[StateMachine] Run {run_id} já terminou ({run.state})")
            return run

        run.state = RunState.RUNNING
        step_id = run.current_step_id

        if step_id not in self.definition.steps:
            run.state = RunState.FAILED
            run.error = f"Step inválido: {step_id}"
            self._save_run(run)
            return run

        step_def = self.definition.steps[step_id]
        step_run = run.steps[step_id]

        # Verificar condição de guarda
        if step_def.condition:
            try:
                should_run = bool(eval(step_def.condition, {"ctx": run.context}))  # noqa: S307
            except Exception as e:
                logger.warning(f"[StateMachine] Condição inválida em {step_id}: {e}")
                should_run = True

            if not should_run:
                logger.info(f"[StateMachine] Passo {step_id} ignorado (condição falsa)")
                step_run.state = StepState.SKIPPED
                run = self._advance(run, step_id, success=True)
                self._save_run(run)
                return run

        # Executar passo
        step_run.state = StepState.RUNNING
        step_run.attempts += 1
        step_run.started_at = datetime.now().isoformat()
        self._save_run(run)

        success = False
        result = ""
        try:
            if self._step_executor:
                result = self._step_executor(step_def, run)
                success = True
            else:
                # Modo simulação (sem executor real)
                result = f"[sim] Passo '{step_def.name}' concluído"
                success = True
        except Exception as e:
            result = str(e)
            logger.error(f"[StateMachine] Erro em {step_id}: {e}")

        step_run.finished_at = datetime.now().isoformat()
        step_run.result = result

        if success:
            step_run.state = StepState.COMPLETED
            # Guardar output no contexto para passos seguintes
            run.context[f"{step_id}_result"] = result
        else:
            # Tentar retry
            if step_run.attempts <= step_def.max_retries:
                logger.info(f"[StateMachine] Retry {step_run.attempts}/{step_def.max_retries} em {step_id}")
                step_run.state = StepState.PENDING
                run.updated_at = datetime.now().isoformat()
                self._save_run(run)
                return run
            else:
                step_run.state = StepState.FAILED

        run = self._advance(run, step_id, success=success)
        run.updated_at = datetime.now().isoformat()
        self._save_run(run)
        return run

    def _advance(self, run: WorkflowRun, step_id: str, success: bool) -> WorkflowRun:
        """Calcula o próximo estado após um passo."""
        step_def = self.definition.steps[step_id]
        transition = step_def.on_success if success else step_def.on_failure

        if transition == "end" or (transition == "next" and not self._next_step(step_id)):
            run.state = RunState.COMPLETED
            run.current_step_id = ""
            logger.info(f"[StateMachine] Run {run.run_id} COMPLETADA [OK]")
        elif transition == "fail":
            run.state = RunState.FAILED
            run.error = f"Passo {step_id} falhou e on_failure=fail"
            logger.warning(f"[StateMachine] Run {run.run_id} FALHOU em {step_id}")
        elif transition == "next":
            next_id = self._next_step(step_id)
            run.current_step_id = next_id
            logger.info(f"[StateMachine] {step_id} → {next_id}")
        else:
            # Transição direta para step específico
            if transition in self.definition.steps:
                run.current_step_id = transition
                logger.info(f"[StateMachine] {step_id} → {transition} (directo)")
            else:
                run.state = RunState.FAILED
                run.error = f"Transição inválida: {transition}"

        return run

    def _next_step(self, step_id: str) -> Optional[str]:
        """Retorna o ID do próximo passo por ordem de definição."""
        step_ids = list(self.definition.steps.keys())
        try:
            idx = step_ids.index(step_id)
            if idx + 1 < len(step_ids):
                return step_ids[idx + 1]
        except ValueError:
            pass
        return None

    # ── Persistência ────────────────────────────────────────────────────────────

    def _save_run(self, run: WorkflowRun) -> None:
        path = self.RUNS_DIR / f"{run.run_id}.json"
        path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_run(self, run_id: str) -> Optional[WorkflowRun]:
        path = self.RUNS_DIR / f"{run_id}.json"
        if not path.exists():
            return None
        return WorkflowRun.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def get_state(self, run_id: str) -> Optional[WorkflowRun]:
        return self._load_run(run_id)

    def list_runs(self, workflow_name: Optional[str] = None) -> list[dict]:
        """Lista runs, opcionalmente filtradas por workflow."""
        runs = []
        for f in self.RUNS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if workflow_name and data.get("workflow_name") != workflow_name:
                    continue
                runs.append({
                    "run_id": data["run_id"],
                    "workflow_name": data["workflow_name"],
                    "state": data["state"],
                    "current_step": data.get("current_step_id", ""),
                    "created_at": data.get("created_at", ""),
                })
            except Exception:
                pass
        return sorted(runs, key=lambda r: r["created_at"], reverse=True)

    # ── Utilitários ─────────────────────────────────────────────────────────────

    def summary(self, run_id: str) -> str:
        """Retorna resumo legível de uma run."""
        run = self._load_run(run_id)
        if not run:
            return f"Run {run_id} não encontrada"

        lines = [
            f"Run: {run.run_id}  |  Workflow: {run.workflow_name}  |  Estado: {run.state}",
            "",
        ]
        for step_id, step_def in self.definition.steps.items():
            step_run = run.steps.get(step_id, StepRun(step_id=step_id))
            icon = {
                StepState.PENDING: "⏳",
                StepState.RUNNING: "[LOOP]",
                StepState.COMPLETED: "[OK]",
                StepState.FAILED: "[X]",
                StepState.SKIPPED: "⏭️",
            }.get(step_run.state, "?")
            lines.append(f"  {icon} {step_def.name} [{step_run.state}]")
            if step_run.result:
                short = step_run.result[:80].replace("\n", " ")
                lines.append(f"     → {short}")

        if run.error:
            lines.append(f"\nErro: {run.error}")

        return "\n".join(lines)
