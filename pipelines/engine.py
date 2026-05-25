"""
pipelines/engine.py — Motor de execucao de pipelines multi-agente.

Executa pipelines passo a passo, gerindo dependencias
e passagem de contexto entre passos.
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config
from core.bus import bus
from .models import Pipeline, PipelineStep, PipelineStatus

logger = logging.getLogger(__name__)


class PipelineEngine:
    """
    Motor de pipelines.

    Uso:
        engine = PipelineEngine()
        pipeline = engine.create_pipeline("Dev Cycle", [
            {"name": "Analisar", "agent_role": "explorador", "task_template": "Analisa..."},
            {"name": "Implementar", "agent_role": "developer", "task_template": "Implementa..."},
            {"name": "Testar", "agent_role": "qa_tester", "task_template": "Testa..."},
        ])
        await engine.run(pipeline.id)
    """

    def __init__(self):
        self.config = Config
        self.pipelines_dir = self.config.PIPELINES_DIR / "definitions"
        self.pipelines_dir.mkdir(parents=True, exist_ok=True)
        self._running: dict[str, asyncio.Task] = {}

    def create_pipeline(self, name: str, steps_config: list[dict],
                        description: str = "") -> Pipeline:
        """Cria um novo pipeline."""
        steps = []
        for i, sc in enumerate(steps_config):
            step = PipelineStep(
                name=sc.get("name", f"Passo {i+1}"),
                agent_role=sc.get("agent_role", "developer"),
                task_template=sc.get("task_template", ""),
                depends_on=sc.get("depends_on", []),
                order=i,
            )
            steps.append(step)

        pipeline = Pipeline(name=name, description=description, steps=steps)
        self._save(pipeline)
        logger.info(f"[Pipeline] Criado: {name} ({pipeline.id[:8]})")
        return pipeline

    async def run(self, pipeline_id: str) -> dict:
        """Executa um pipeline."""
        pipeline = self._load(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline nao encontrado"}

        pipeline.status = PipelineStatus.RUNNING
        pipeline.updated_at = datetime.now().isoformat()
        self._save(pipeline)

        results = []
        for step in pipeline.steps:
            logger.info(f"[Pipeline] Executando passo: {step.name}")

            # Verificar dependencias
            deps_met = all(
                any(s.id == dep and s.status == PipelineStatus.COMPLETED for s in pipeline.steps)
                for dep in step.depends_on
            )
            if not deps_met:
                step.status = PipelineStatus.FAILED
                step.result = "Dependencias nao cumpridas"
                continue

            step.status = PipelineStatus.RUNNING
            self._save(pipeline)

            # TODO: Integrar com TaskQueue para criar tarefa real
            # Por agora, apenas simula
            step.status = PipelineStatus.COMPLETED
            step.result = f"Passo {step.name} concluido"
            results.append({"step": step.name, "status": "ok"})

        pipeline.status = PipelineStatus.COMPLETED
        pipeline.updated_at = datetime.now().isoformat()
        self._save(pipeline)

        logger.info(f"[Pipeline] Concluido: {pipeline.name}")
        return {"pipeline_id": pipeline.id, "results": results}

    def _save(self, pipeline: Pipeline) -> None:
        path = self.pipelines_dir / f"{pipeline.id}.json"
        path.write_text(json.dumps(pipeline.to_dict(), indent=2), encoding="utf-8")

    def _load(self, pipeline_id: str) -> Optional[Pipeline]:
        path = self.pipelines_dir / f"{pipeline_id}.json"
        if not path.exists():
            # Tentar por prefixo
            for f in self.pipelines_dir.glob("*.json"):
                if f.stem.startswith(pipeline_id):
                    path = f
                    break
            else:
                return None
        data = json.loads(path.read_text(encoding="utf-8"))
        steps = [
            PipelineStep(
                id=s["id"], name=s["name"], agent_role=s["agent_role"],
                task_template=s["task_template"], depends_on=s.get("depends_on", []),
                status=PipelineStatus(s["status"]), result=s.get("result", ""),
                task_id=s.get("task_id", ""), order=s.get("order", 0),
            )
            for s in data.get("steps", [])
        ]
        return Pipeline(
            id=data["id"], name=data["name"], description=data.get("description", ""),
            steps=steps, status=PipelineStatus(data["status"]),
            created_at=data.get("created_at", ""), updated_at=data.get("updated_at", ""),
        )

    def list_pipelines(self) -> list[dict]:
        """Lista todos os pipelines."""
        pipelines = []
        for f in self.pipelines_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            pipelines.append({
                "id": data["id"],
                "name": data["name"],
                "status": data["status"],
                "steps": len(data.get("steps", [])),
                "created_at": data.get("created_at", ""),
            })
        return sorted(pipelines, key=lambda p: p["created_at"], reverse=True)
