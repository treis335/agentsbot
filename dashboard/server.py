"""
dashboard/server.py — Servidor do dashboard web (Batch 8 upgrade).

Serve:
  /         -> live.html  (feed SSE em tempo real + métricas)
  /costs    -> costs.html (custos por agente/modelo + traces)
  /api/*    -> proxy para a API REST em :8080
"""
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES = Path(__file__).parent / "templates"


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler do dashboard — serve HTML + proxy para a API."""

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"

        if path.startswith("/api/"):
            self._proxy_api(self.path)
        elif path in ("/costs",):
            self._serve_template("costs.html")
        else:
            self._serve_template("live.html")

    def _serve_template(self, name: str) -> None:
        tpl = _TEMPLATES / name
        if not tpl.exists():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Template not found")
            return
        content = tpl.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _proxy_api(self, full_path: str) -> None:
        import urllib.request
        api_path = full_path[4:]  # remove /api
        try:
            with urllib.request.urlopen(
                f"http://localhost:8080{api_path}", timeout=8
            ) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        logger.debug(f"[Dashboard] {args[0]} {args[1]} {args[2]}")


def start_dashboard(host: str = "0.0.0.0", port: int = 3000):
    """Inicia o servidor do dashboard."""
    server = HTTPServer((host, port), DashboardHandler)
    logger.info(f"[Dashboard] http://{host}:{port}  (live feed + custos)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
