"""
dashboard/server.py — Servidor do dashboard web.

Interface visual para monitorizar e controlar o ecossistema.
"""
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

logger = logging.getLogger(__name__)

HTML = r"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Correoto Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,-apple-system,sans-serif}
body{background:#0d1117;color:#c9d1d9;padding:20px}
h1{color:#58a6ff;margin-bottom:20px;font-size:24px}
h2{color:#8b949e;font-size:16px;margin:20px 0 10px;text-transform:uppercase;letter-spacing:1px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:30px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}
.card h3{color:#58a6ff;font-size:14px;margin-bottom:8px}
.card .value{font-size:28px;font-weight:700;color:#fff}
.card .label{font-size:12px;color:#8b949e;margin-top:4px}
table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #21262d;font-size:13px}
th{color:#8b949e;font-weight:600}
.status-healthy{color:#3fb950}
.status-warning{color:#d29922}
.status-error{color:#f85149}
.status-idle{color:#8b949e}
.status-running{color:#3fb950}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.badge-ok{background:#3fb95022;color:#3fb950;border:1px solid #3fb95044}
.badge-warn{background:#d2992222;color:#d29922;border:1px solid #d2992244}
.badge-err{background:#f8514922;color:#f85149;border:1px solid #f8514944}
.refresh{text-align:right;margin-bottom:10px;font-size:12px;color:#8b949e}
</style>
</head>
<body>
<h1>Correoto Dashboard</h1>
<div class="refresh">Ultima atualizacao: <span id="lastUpdate">-</span></div>

<div class="grid" id="stats">
<div class="card"><h3>Agentes</h3><div class="value" id="agentCount">-</div><div class="label">Total de agentes</div></div>
<div class="card"><h3>Tarefas</h3><div class="value" id="taskCount">-</div><div class="label">Total de tarefas</div></div>
<div class="card"><h3>Tool Calls</h3><div class="value" id="toolCalls">-</div><div class="label">Total de chamadas</div></div>
<div class="card"><h3>Tokens</h3><div class="value" id="tokenCount">-</div><div class="label">Total gastos</div></div>
<div class="card"><h3>Sucesso</h3><div class="value" id="successRate">-</div><div class="label">Taxa de sucesso</div></div>
<div class="card"><h3>Erros</h3><div class="value" id="errorCount">-</div><div class="label">Total de erros</div></div>
</div>

<h2>Agentes</h2>
<table id="agentsTable"><thead><tr><th>Nome</th><th>Role</th><th>Status</th><th>ID</th></tr></thead><tbody></tbody></table>

<h2>Tarefas</h2>
<table id="tasksTable"><thead><tr><th>Titulo</th><th>Status</th><th>Atribuido a</th></tr></thead><tbody></tbody></table>

<script>
async function loadData(){
try{
const [agents,tasks,metrics]=await Promise.all([
fetch('/api/agents').then(r=>r.json()),
fetch('/api/tasks').then(r=>r.json()),
fetch('/api/metrics').then(r=>r.json()),
]);
document.getElementById('agentCount').textContent=agents.total||0;
document.getElementById('taskCount').textContent=tasks.total||0;
document.getElementById('toolCalls').textContent=metrics.tool_calls?.total||0;
document.getElementById('tokenCount').textContent=metrics.token_usage?.total||0;
document.getElementById('successRate').textContent=(metrics.success_rate||100)+'%';
document.getElementById('errorCount').textContent=metrics.errors?.total||0;

const agentsBody=document.querySelector('#agentsTable tbody');
agentsBody.innerHTML=(agents.agents||[]).map(a=>
`<tr><td>${a.name}</td><td>${a.role}</td><td class="status-${a.status}">${a.status}</td><td>${a.id}</td></tr>`
).join('');

const tasksBody=document.querySelector('#tasksTable tbody');
tasksBody.innerHTML=(tasks.tasks||[]).map(t=>
`<tr><td>${t.title}</td><td class="status-${t.status}">${t.status}</td><td>${t.assigned_to||'-'}</td></tr>`
).join('');

document.getElementById('lastUpdate').textContent=new Date().toLocaleTimeString();
}catch(e){console.error(e)}
}
loadData();
setInterval(loadData,5000);
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler para o dashboard web."""

    def do_GET(self):
        if self.path.startswith("/api/"):
            # Proxy para a API
            import urllib.request
            api_path = self.path[4:]  # Remove /api
            try:
                with urllib.request.urlopen(f"http://localhost:8080{api_path}", timeout=5) as resp:
                    data = resp.read().decode()
                    self.send_response(resp.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data.encode())
            except Exception as e:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))

    def log_message(self, format, *args):
        logger.debug(f"[Dashboard] {args[0]} {args[1]} {args[2]}")


def start_dashboard(host: str = "0.0.0.0", port: int = 3000):
    """Inicia o servidor do dashboard."""
    server = HTTPServer((host, port), DashboardHandler)
    logger.info(f"[Dashboard] http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
