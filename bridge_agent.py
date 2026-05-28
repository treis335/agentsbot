"""
bridge_agent.py — Ponte entre o Supervisor (sandbox) e o PC local
Permite ao Supervisor executar comandos, ler/escrever ficheiros,
e sincronizar com o GitHub diretamente no teu PC.
Corre como processo oculto, escuta comandos do Supervisor.
"""
import json, os, subprocess, socket, threading, datetime, time
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
AGENTS_FILE = BASE_DIR / "agents.json"
MEMORY_DIR = BASE_DIR / "memory"
BRIDGE_LOG = MEMORY_DIR / "bridge_log.json"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

class BridgeAgent:
    def __init__(self):
        self.running = True
        self.port = 9999
        self.server = None
        self.log("BridgeAgent iniciado")
    
    def log(self, msg):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[BridgeAgent] [{ts}] {msg}")
        logs = []
        if BRIDGE_LOG.exists():
            with open(BRIDGE_LOG, "r", encoding="utf-8") as f:
                logs = json.load(f)
        logs.append({"ts": ts, "msg": msg})
        with open(BRIDGE_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    
    def executar_comando(self, comando):
        try:
            self.log(f"Executando: {comando[:100]}...")
            r = subprocess.run(
                comando, shell=True, capture_output=True, text=True, timeout=30
            )
            return {"stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Timeout (30s)", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}
    
    def git_status(self):
        return self.executar_comando(f'cd /d "{BASE_DIR}" && git status')
    
    def git_push(self, msg=None):
        if not msg:
            msg = f"Bridge auto-sync {datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        cmd = f'cd /d "{BASE_DIR}" && git add -A && git commit -m "{msg}" && git push origin main'
        return self.executar_comando(cmd)
    
    def ler_ficheiro(self, path):
        full_path = BASE_DIR / path
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return {"sucesso": True, "conteudo": f.read()}
        return {"sucesso": False, "erro": "Ficheiro não encontrado"}
    
    def escrever_ficheiro(self, path, conteudo):
        full_path = BASE_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(conteudo)
        self.log(f"Ficheiro escrito: {path}")
        return {"sucesso": True}
    
    def iniciar_servidor(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind(("127.0.0.1", self.port))
            self.server.listen(5)
            self.server.settimeout(1.0)
            self.log(f"Servidor a escutar em 127.0.0.1:{self.port}")
            
            while self.running:
                try:
                    conn, addr = self.server.accept()
                    threading.Thread(target=self.processar_comando, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
        except Exception as e:
            self.log(f"Erro no servidor: {e}")
        finally:
            if self.server:
                self.server.close()
    
    def processar_comando(self, conn, addr):
        self.log(f"Conexão de {addr}")
        try:
            data = conn.recv(65536).decode("utf-8")
            comando = json.loads(data)
            acao = comando.get("acao", "")
            
            if acao == "executar":
                resultado = self.executar_comando(comando["comando"])
            elif acao == "git_push":
                resultado = self.git_push(comando.get("msg"))
            elif acao == "git_status":
                resultado = self.git_status()
            elif acao == "ler":
                resultado = self.ler_ficheiro(comando["path"])
            elif acao == "escrever":
                resultado = self.escrever_ficheiro(comando["path"], comando["conteudo"])
            else:
                resultado = {"erro": f"Ação desconhecida: {acao}"}
            
            conn.send(json.dumps(resultado).encode("utf-8"))
        except Exception as e:
            conn.send(json.dumps({"erro": str(e)}).encode("utf-8"))
        finally:
            conn.close()
    
    def start(self):
        self.log("🔥 BridgeAgent 24/7 — Pronto para comandos do Supervisor")
        self.iniciar_servidor()

if __name__ == "__main__":
    agent = BridgeAgent()
    agent.start()
