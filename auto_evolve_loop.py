"""
auto_evolve_loop.py — Loop infinito de evolução autónoma
Corre 24/7, usa evolution_engine + bridge_agent
Sem intervenção humana
"""
import time, json, os, sys, subprocess, threading
from pathlib import Path

BASE_DIR = Path("C:/Users/Crypto Bull/Desktop/Agente Local")
os.chdir(BASE_DIR)

class AutoEvolveLoop:
    def __init__(self):
        self.iteration = 0
        self.evolution_cycles = 0
        self.running = True

    def log(self, msg):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] {msg}")

    def run_evolution_engine(self):
        try:
            from evolution_engine import EvolutionEngine
            engine = EvolutionEngine()
            result = engine.run_evolution_cycle()
            self.evolution_cycles += 1
            return result
        except Exception as e:
            self.log(f"[X] Erro evolution_engine: {e}")
            return None

    def run_bridge_agent(self):
        try:
            from bridge_agent import BridgeAgent
            bridge = BridgeAgent()
            bridge.log("BridgeAgent ativado pelo loop")
            return bridge
        except Exception as e:
            self.log(f"[X] Erro bridge_agent: {e}")
            return None

    def git_sync(self):
        try:
            subprocess.run(["git", "add", "."], capture_output=True, cwd=BASE_DIR)
            result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True, cwd=BASE_DIR)
            if result.returncode != 0:
                msg = f"Auto-evolu??o ciclo #{self.evolution_cycles}"
                subprocess.run(["git", "commit", "-m", msg], capture_output=True, cwd=BASE_DIR)
                subprocess.run(["git", "push"], capture_output=True, cwd=BASE_DIR)
                self.log(f"[OK] Git commit & push: {msg}")
                return True
        except Exception as e:
            self.log(f"[!] Git sync: {e}")
        return False

    def check_system_health(self):
        agents_file = BASE_DIR / "agents.json"
        if not agents_file.exists():
            self.log("[X] agents.json n?o encontrado!")
            return False
        try:
            with open(agents_file) as f:
                agents = json.load(f)
            self.log(f"[HOSP] Sa?de OK ? {len(agents)} agentes ativos")
            return True
        except:
            self.log("[X] agents.json corrompido!")
            return False

    def run_cycle(self):
        self.iteration += 1
        self.log(f"\n{'='*60}")
        self.log(f"[START] CICLO #{self.iteration}")
        self.log(f"{'='*60}")

        self.check_system_health()
        result = self.run_evolution_engine()
        
        if result:
            self.log(f"   Agentes: {result['agentes']} | Issues: {result['issues']}")
            if result.get('novo_agente'):
                self.log(f"   [NEW] Novo agente criado: {result['novo_agente']}")
            if result.get('commit'):
                self.log(f"   [OK] Git push feito")

        if self.iteration % 3 == 0:
            self.git_sync()

        self.log(f"[OK] Ciclo #{self.iteration} completo")
        return result

    def start(self):
        self.log("[FOGO] AutoEvolveLoop 24/7 ? EvolutionEngine + BridgeAgent ativos!")
        self.log("[SINAL] A evoluir autonomamente...")
        
        while self.running:
            try:
                self.run_cycle()
                time.sleep(60)
            except KeyboardInterrupt:
                self.log("[STOP] Paragem solicitada")
                self.running = False
            except Exception as e:
                self.log(f"[EXPL] Erro cr?tico: {e}")
                time.sleep(10)

if __name__ == "__main__":
    loop = AutoEvolveLoop()
    loop.start()
