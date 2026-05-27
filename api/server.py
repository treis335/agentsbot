"""
api/server.py — Servidor API REST para o dashboard e controlo externo.

Endpoints:
- GET  /health          — Saude do sistema
- GET  /agents          — Listar agentes
- GET  /agents/<id>     — Detalhes de um agente
- POST /agents          — Criar agente
- GET  /tasks           — Listar tarefas
- POST /tasks           — Criar tarefa
- GET  /metrics         — Metricas do sistema
- GET  /memory          — Memoria global
- GET  /audit           — Logs de auditoria
"""
import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class APIHandler(BaseHTTPRequestHandler):
    """Handler HTTP para a API REST."""

    # Referencias aos componentes (setadas externamente)
    agent_manager = None
    task_queue = None
    global_memory = None
    metrics_collector = None
    audit_logger = None

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode())

    def _send_error(self, message: str, status: int = 400):
        self._send_json({"error": message}, status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        try:
            if path in ("/health", "/api/health"):
                self._handle_health()
            elif path in ("/agents", "/api/agents"):
                self._handle_list_agents()
            elif path.startswith("/agents/") or path.startswith("/api/agents/"):
                agent_id = path.split("/")[-1]
                self._handle_get_agent(agent_id)
            elif path in ("/tasks", "/api/tasks"):
                self._handle_list_tasks()
            elif path in ("/metrics", "/api/metrics"):
                self._handle_metrics()
            elif path in ("/memory", "/api/memory"):
                self._handle_memory()
            elif path in ("/audit", "/api/audit"):
                self._handle_audit()
            elif path in ("/costs", "/api/costs"):
                self._handle_costs(params)
            elif path in ("/traces", "/api/traces"):
                self._handle_traces(params)
            elif path in ("/events", "/api/events"):
                self._handle_events_sse()
            elif path in ("/routing", "/api/routing"):
                self._handle_routing_stats()
            else:
                self._send_error("Endpoint nao encontrado", 404)
        except Exception as e:
            logger.error(f"[API] Erro: {e}")
            self._send_error(str(e), 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        try:
            if path in ("/agents", "/api/agents"):
                self._handle_create_agent(data)
            elif path in ("/tasks", "/api/tasks"):
                self._handle_create_task(data)
            elif path in ("/shutdown", "/api/shutdown"):
                self._handle_shutdown()
            else:
                self._send_error("Endpoint nao encontrado", 404)
        except Exception as e:
            logger.error(f"[API] Erro: {e}")
            self._send_error(str(e), 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --- Handlers ---

    def _handle_health(self):
        self._send_json({
            "status": "ok",
            "version": "2.0",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

    def _handle_list_agents(self):
        if not self.agent_manager:
            self._send_error("Agent manager nao disponivel")
            return
        agents = self.agent_manager.list_agents()
        self._send_json({
            "total": len(agents),
            "agents": [{"id": a.id[:8], "name": a.name, "role": a.role.value,
                        "status": a.status.value} for a in agents],
        })

    def _handle_get_agent(self, agent_id: str):
        if not self.agent_manager:
            self._send_error("Agent manager nao disponivel")
            return
        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            self._send_error("Agente nao encontrado", 404)
            return
        self._send_json(agent.to_dict())

    def _handle_create_agent(self, data: dict):
        if not self.agent_manager:
            self._send_error("Agent manager nao disponivel")
            return
        name = data.get("name", "")
        soul = data.get("soul", "")
        if not name or not soul:
            self._send_error("name e soul sao obrigatorios")
            return
        agent = self.agent_manager.create_agent(name, soul)
        self._send_json({"id": agent.id[:8], "name": agent.name}, 201)

    def _handle_list_tasks(self):
        if not self.task_queue:
            self._send_error("Task queue nao disponivel")
            return
        tasks = self.task_queue.list_tasks()
        self._send_json({
            "total": len(tasks),
            "tasks": [{"id": t.id[:8], "title": t.title, "status": t.status.value,
                       "assigned_to": t.assigned_to[:8] if t.assigned_to else ""}
                      for t in tasks],
        })

    def _handle_create_task(self, data: dict):
        if not self.task_queue:
            self._send_error("Task queue nao disponivel")
            return
        title = data.get("title", "")
        if not title:
            self._send_error("title e obrigatorio")
            return
        task = self.task_queue.create_task(
            title=title,
            description=data.get("description", ""),
            created_by=data.get("created_by", "api"),
        )
        self._send_json({"id": task.id[:8], "title": task.title}, 201)

    def _handle_metrics(self):
        if not self.metrics_collector:
            self._send_error("Metrics collector nao disponivel")
            return
        self._send_json(self.metrics_collector.get_report())

    def _handle_memory(self):
        if not self.global_memory:
            self._send_error("Global memory nao disponivel")
            return
        self._send_json(self.global_memory.get_all())

    def _handle_audit(self):
        if not self.audit_logger:
            self._send_error("Audit logger nao disponivel")
            return
        self._send_json({"logs": self.audit_logger.get_logs(limit=100)})

    def _handle_shutdown(self):
        self._send_json({"message": "Shutdown signal received"})
        # Sinalizar shutdown em background
        import threading
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _handle_costs(self, params: dict) -> None:
        """GET /api/costs — custos acumulados por agente/modelo."""
        from monitoring.agent_trace import cost_summary
        days = int(params.get("days", ["1"])[0])
        days = min(max(days, 1), 30)  # clamp 1-30
        data = cost_summary(days=days)
        # Enriquecer com dados in-memory do MetricsCollector
        try:
            report = self.server._metrics.get_report()
            data["realtime_cost_usd"] = report["token_usage"].get("total_cost_usd", 0.0)
            data["realtime_tokens"] = report["token_usage"]["total"]
            data["by_model_realtime"] = report["token_usage"].get("by_model", {})
        except Exception:
            pass
        self._send_json(data)

    def _handle_traces(self, params: dict) -> None:
        """GET /api/traces — traces de execução dos agentes."""
        from monitoring.agent_trace import load_traces
        days = int(params.get("days", ["1"])[0])
        limit = int(params.get("limit", ["50"])[0])
        agent = params.get("agent", [None])[0]
        traces = load_traces(days=days, agent_name=agent, limit=limit)
        self._send_json({"traces": traces, "total": len(traces)})

    def _handle_events_sse(self) -> None:
        """
        GET /api/events — Server-Sent Events live feed do event bus.
        Envia os últimos eventos e fica à escuta de novos via bus history.
        Para clientes SSE (dashboard live).
        """
        from core.bus import bus
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            # Enviar histórico recente (últimos 20 eventos)
            history = bus.get_history(limit=20)
            for event in history:
                data = json.dumps(event, ensure_ascii=False, default=str)
                self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                self.wfile.flush()

            # Heartbeat para manter a ligação aberta
            import time
            for _ in range(30):  # max 30s de stream
                time.sleep(1)
                self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # cliente desligou
        except Exception as e:
            logger.debug(f"[API/SSE] Ligação terminada: {e}")

    def _handle_routing_stats(self) -> None:
        """GET /api/routing — estatísticas do inference router (local vs cloud)."""
        try:
            from inference.router import router
            self._send_json(router.stats())
        except Exception as e:
            self._send_json({"error": str(e), "local_calls": 0, "cloud_calls": 0})

    def log_message(self, format, *args):
        logger.debug(f"[API] {args[0]} {args[1]} {args[2]}")


def start_api(host: str = "0.0.0.0", port: int = 8080,
              agent_manager=None, task_queue=None,
              global_memory=None, metrics_collector=None,
              audit_logger=None):
    """
    Inicia o servidor API.

    Args:
        host: Host para bind
        port: Porta para bind
        agent_manager: Instancia de AgentManager
        task_queue: Instancia de TaskQueue
        global_memory: Instancia de GlobalMemory
        metrics_collector: Instancia de MetricsCollector
        audit_logger: Instancia de AuditLogger
    """
    APIHandler.agent_manager = agent_manager
    APIHandler.task_queue = task_queue
    APIHandler.global_memory = global_memory
    APIHandler.metrics_collector = metrics_collector
    APIHandler.audit_logger = audit_logger

    server = HTTPServer((host, port), APIHandler)
    logger.info(f"[API] Servidor a correr em http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("[API] Servidor parado.")
        server.server_close()
