"""dashboard/server.py - Servidor do dashboard web com API real e SSE."""
import json, logging, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
import sys

# Adicionar raiz ao path para importar metrics_collector
_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root))

logger = logging.getLogger(__name__)
_TEMPLATES = Path(__file__).parent / "templates"

# Import metrics collector
try:
    from dashboard.api.metrics_collector import MetricsCollector
    collector = MetricsCollector()
except Exception as e:
    logger.warning(f"MetricsCollector nao disponivel: {e}")
    collector = None


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler do dashboard - serve HTML + API real + SSE."""

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"

        if path == "/api/metrics":
            self._serve_metrics()
        elif path == "/api/health":
            self._serve_health()
        elif path.startswith("/api/"):
            self._proxy_api(self.path)
        elif path in ("/costs",):
            self._serve_template("costs.html")
        else:
            self._serve_template("live.html")

    def _serve_metrics(self):
        """Serve metricas reais do ecossistema como JSON."""
        if collector is None:
            data = {"error": "MetricsCollector nao disponivel", "timestamp": datetime.now().isoformat()}
        else:
            try:
                data = collector.collect()
            except Exception as e:
                data = {"error": str(e), "timestamp": datetime.now().isoformat()}
        payload = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_health(self):
        payload = json.dumps({"status": "ok", "timestamp": datetime.now().isoformat()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

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
        api_path = full_path[4:]
        try:
            with urllib.request.urlopen(f"http://localhost:8080{api_path}", timeout=8) as resp:
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
    server = HTTPServer((host, port), DashboardHandler)
    logger.info(f"[Dashboard] http://{host}:{port}")
    print(f"[Dashboard] A correr em http://{host}:{port}")
    print(f"[Dashboard] Metricas: http://{host}:{port}/api/metrics")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_dashboard()
