"""
api/server.py â€” Servidor API REST para o dashboard e controlo externo.

Endpoints:
- GET  /health          â€” Saude do sistema
- GET  /agents          â€” Listar agentes
- GET  /agents/<id>     â€” Detalhes de um agente
- POST /agents          â€” Criar agente
- GET  /tasks           â€” Listar tarefas
- POST /tasks           â€” Criar tarefa
- GET  /metrics         â€” Metricas do sistema
- GET  /memory          â€” Memoria global
- GET  /audit           â€” Logs de auditoria
"""
import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional
from pathlib import Path

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
            elif path in ("/memory_stats", "/api/memory_stats"):
                self._handle_memory_stats()
            elif path in ("/dashboard",):
                self._handle_dashboard()
            elif path in ("/api/ecosystem/status", "/ecosystem/status"):
                self._handle_ecosystem_status()
            elif path in ("/api/chat", "/chat"):
                self._handle_chat()
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
            elif path in ("/api/chat", "/chat"):
                self._handle_chat_post(data)
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
        """GET /api/costs â€” custos acumulados por agente/modelo."""
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
        """GET /api/traces â€” traces de execuÃ§Ã£o dos agentes."""
        from monitoring.agent_trace import load_traces
        days = int(params.get("days", ["1"])[0])
        limit = int(params.get("limit", ["50"])[0])
        agent = params.get("agent", [None])[0]
        traces = load_traces(days=days, agent_name=agent, limit=limit)
        self._send_json({"traces": traces, "total": len(traces)})

    def _handle_events_sse(self) -> None:
        """
        GET /api/events â€” Server-Sent Events live feed do event bus.
        Envia os Ãºltimos eventos e fica Ã  escuta de novos via bus history.
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
            # Enviar histÃ³rico recente (Ãºltimos 20 eventos)
            history = bus.get_history(limit=20)
            for event in history:
                data = json.dumps(event, ensure_ascii=False, default=str)
                self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                self.wfile.flush()

            # Heartbeat para manter a ligaÃ§Ã£o aberta
            import time
            for _ in range(30):  # max 30s de stream
                time.sleep(1)
                self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # cliente desligou
        except Exception as e:
            logger.debug(f"[API/SSE] Liga????o terminada: {e}")

    def _handle_routing_stats(self) -> None:
        """GET /api/routing â€” estatÃ­sticas do inference router (local vs cloud)."""
        try:
            from inference.router import router
            self._send_json(router.stats())
        except Exception as e:
            self._send_json({"error": str(e), "local_calls": 0, "cloud_calls": 0})

    def _handle_memory_stats(self) -> None:
        """GET /api/memory_stats — estatísticas da memória episódica do loop."""
        try:
            from memory.loop_memory import get_loop_memory
            mem = get_loop_memory()
            data = mem.stats()
            data["recent_failures"] = mem.recent_failures(limit=5)
            data["total_episodes"] = len(mem._episodes)
            self._send_json(data)
        except Exception as e:
            self._send_json({"error": str(e), "total_episodes": 0})

    def log_message(self, format, *args):
        logger.debug(f"[API] {args[0]} {args[1]} {args[2]}")


    def _handle_dashboard(self):
        """Serve o dashboard HTML."""
        dashboard_path = Path(__file__).parent.parent / "dashboard" / "templates" / "live.html"
        if dashboard_path.exists():
            content = dashboard_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        else:
            self._send_error("Dashboard nao encontrado", 404)

    def _handle_ecosystem_status(self):
        """Devolve o estado atual do ecossistema em JSON com dados reais."""
        import json, datetime
        from pathlib import Path

        base_dir = Path(__file__).parent.parent

        # --- AGENTES: tentar AgentManager primeiro, depois ficheiros ---
        agents = 0
        agent_names = []
        try:
            if self.server.agent_manager:
                agent_list = self.server.agent_manager.list_agents()
                agents = len(agent_list)
                agent_names = [{"name": a.name, "role": str(a.role).split(".")[-1]} for a in agent_list]
        except Exception:
            pass

        if not agents:
            # Fallback: ler ficheiros directamente
            for candidate in [
                base_dir / "agents" / "registry" / "agents.json",
                base_dir / "agents.json",
            ]:
                if candidate.exists():
                    try:
                        data = json.loads(candidate.read_text(encoding="utf-8"))
                        lst = data if isinstance(data, list) else data.get("agents", [])
                        agents = len(lst)
                        agent_names = [{"name": a.get("name", a.get("id", "?")), "role": a.get("role","agent")} for a in lst[:50]]
                        break
                    except Exception:
                        pass

        # --- TAREFAS ---
        tasks_done = tasks_pending = tasks_failed = 0
        all_tasks = []
        for bf in [base_dir / "memory" / "backlog.json", base_dir / "tasks" / "backlog.json"]:
            if bf.exists():
                try:
                    tasks = json.loads(bf.read_text(encoding="utf-8"))
                    if not isinstance(tasks, list):
                        tasks = tasks.get("tasks", [])
                    for t in tasks:
                        s = t.get("status", "").lower()
                        if s in ("done","completed","concluida","concluído","success"):
                            tasks_done += 1
                        elif s in ("failed","error","falhou","failed"):
                            tasks_failed += 1
                        else:
                            tasks_pending += 1
                    all_tasks = tasks
                    break
                except Exception:
                    pass

        # --- LOGS: ler autonomous_log.md + ficheiros .log ---
        logs = []
        log_sources = [
            base_dir / "memory" / "autonomous_log.md",
            base_dir / "memory" / "evolution_log.json",
            base_dir / "main.log",
            base_dir / "supervisor.log",
        ]
        for lp in log_sources:
            if not lp.exists():
                continue
            try:
                text = lp.read_text(encoding="utf-8", errors="ignore")
                lines = text.strip().splitlines()[-40:]
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    level = "info"
                    ll = line.lower()
                    if any(w in ll for w in ("error","erro","fatal","exception","traceback")):
                        level = "error"
                    elif any(w in ll for w in ("warn","aviso")):
                        level = "warning"
                    elif any(w in ll for w in ("success","ok","[OK]","conclu","done")):
                        level = "success"
                    elif any(w in ll for w in ("agent","agente","supervisor","developer")):
                        level = "agent"
                    t = line[:19] if len(line) > 19 else ""
                    m = line[20:] if len(line) > 20 else line
                    logs.append({"time": t, "message": m[:200], "level": level})
            except Exception:
                pass

        self._send_json({
            "agents": agents,
            "agent_names": agent_names,
            "tasks_done": tasks_done,
            "tasks_pending": tasks_pending,
            "tasks_failed": tasks_failed,
            "tasks": [{"id":t.get("id",""), "title":t.get("title",t.get("desc",t.get("id","?")))[:60], "status":t.get("status","?")} for t in all_tasks[-20:]],
            "logs": logs[-60:],
            "status": "online",
            "timestamp": datetime.datetime.now().isoformat(),
        })





    def _handle_chat(self):
        """Handler GET para chat - devolve historico."""
        self._send_json({"status": "ok", "message": "Usa POST para enviar mensagem"})

    def _handle_chat_post(self, data):
        """Handler POST para chat — chama o LLM real com contexto do ecossistema."""
        import datetime, json
        from pathlib import Path

        msg = data.get("message", "")
        if not msg:
            self._send_error("Mensagem vazia", 400)
            return

        # Construir contexto do ecossistema
        base_dir = Path(__file__).parent.parent
        eco_ctx = ""
        try:
            agents_file = next((p for p in [
                base_dir / "agents" / "registry" / "agents.json",
                base_dir / "agents.json",
            ] if p.exists()), None)
            if agents_file:
                lst = json.loads(agents_file.read_text(encoding="utf-8"))
                if isinstance(lst, dict): lst = lst.get("agents", [])
                names = ', '.join(a.get('name','?') for a in lst[:8])
                eco_ctx += f"Agentes: {len(lst)} ({names})\n"
        except Exception:
            pass

        try:
            bf = base_dir / "memory" / "backlog.json"
            if bf.exists():
                tasks = json.loads(bf.read_text(encoding="utf-8"))
                if not isinstance(tasks, list): tasks = tasks.get("tasks", [])
                done = sum(1 for t in tasks if "done" in t.get("status","").lower() or "complet" in t.get("status","").lower())
                pend = sum(1 for t in tasks if t.get("status","").lower() in ("","pending","pendente","queued"))
                eco_ctx += f"Tarefas: {done} conclu?das, {pend} pendentes\n"
        except Exception:
            pass

        system = """És o Supervisor do ecossistema CORREOTO — um sistema multi-agente autónomo em Python.
O utilizador fala contigo através do dashboard web.

AMBIENTE: Servidor Linux. Tens ferramentas run_shell, run_python, github_api, git_commit_push.
PERSONALIDADE: Directo, proactivo, reportas resultados reais. Nunca inventas resultados.
Se o utilizador pedir algo que requer execução real, diz que vais executar e descreve o plano.

ESTADO ACTUAL DO ECOSSISTEMA:
""" + (eco_ctx or "A carregar...") + """
Responde em português, de forma concisa e útil. Máximo 3 parágrafos."""

        try:
            from core.config import Config
            import urllib.request

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": msg}
            ]
            payload = json.dumps({
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": 600,
            }).encode()
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read().decode())
                response = result["choices"][0]["message"]["content"]
        except Exception as e:
            response = f"Erro ao contactar o LLM: {e}. Verifica DEEPSEEK_API_KEY no .env e que o main.py est? a correr."

        self._send_json({
            "status": "ok",
            "response": response,
            "timestamp": datetime.datetime.now().isoformat(),
        })


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
