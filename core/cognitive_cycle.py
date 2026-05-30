"""
cognitive_cycle.py - Ciclo Cognitivo Integrado v2.0
Pensar -> Agir -> Observar -> Aprender -> Evoluir
Com travao anti-loop corrigido e auto-diagnostico.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
MEMORY_DIR = BASE_DIR / "memory"
CYCLE_STATE_FILE = MEMORY_DIR / "cycle_state.json"
MAX_CYCLES_BEFORE_LEARN = 5
MAX_IDENTICAL_ACTIONS = 3

class CognitiveCycle:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.state = self._load_state()
        
    def _load_state(self):
        if CYCLE_STATE_FILE.exists():
            try:
                with open(CYCLE_STATE_FILE) as f:
                    return json.load(f)
            except: pass
        return {
            "total_cycles": 0,
            "current_phase": "pensar",
            "last_action_key": None,
            "identical_action_count": 0,
            "last_learn_time": 0,
            "errors": [],
            "insights": []
        }
    
    def _save_state(self):
        with open(CYCLE_STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
    
    def pensar(self, context):
        print("[CICLO] Fase: Pensar")
        return {"action": "analyze", "target": "system", "reason": "diagnostico"}
    
    def agir(self, decision):
        action_key = decision.get("action", "unknown")
        print(f"[CICLO] Fase: Agir -> {action_key}")
        return {"result": "ok", "action": action_key}
    
    def observar(self, result):
        action_key = result.get("action", "unknown")
        print(f"[CICLO] Fase: Observar -> {action_key}")
        
        if action_key == self.state.get("last_action_key"):
            self.state["identical_action_count"] += 1
        else:
            self.state["identical_action_count"] = 0
            
        self.state["last_action_key"] = action_key
        return self.state["identical_action_count"] >= MAX_IDENTICAL_ACTIONS
    
    def aprender(self, observation):
        print("[CICLO] Fase: Aprender")
        insight = {
            "timestamp": datetime.now().isoformat(),
            "observation": str(observation),
            "cycle": self.state["total_cycles"]
        }
        self.state["insights"].append(insight)
        self.state["last_learn_time"] = time.time()
        return insight
    
    def evoluir(self, insight):
        print(f"[CICLO] Fase: Evoluir -> {insight['observation']}")
        # Aplicar melhoria baseada no insight
        if insight["observation"] == "loop_detetado":
            self.state["identical_action_count"] = 0
            print("[CICLO] Travao reiniciado apos detecao de loop")
    
    def run_cycle(self, context=""):
        # Verificar travao antes de comecar
        if self.state["identical_action_count"] >= MAX_IDENTICAL_ACTIONS:
            print("[CICLO] TRAVAO ANTI-LOOP ATIVADO")
            insight = self.aprender("loop_detetado")
            self.evoluir(insight)
            return {"status": "travao_ativado", "insight": insight}
        
        # Ciclo normal
        self.state["total_cycles"] += 1
        
        # Pensar
        decision = self.pensar(context)
        
        # Agir
        result = self.agir(decision)
        
        # Observar (devolve True se detetou loop)
        loop_detected = self.observar(result)
        
        # Se detetou loop, aprender e evoluir
        if loop_detected:
            insight = self.aprender("loop_detetado")
            self.evoluir(insight)
        
        # Aprender periodicamente
        if self.state["total_cycles"] % MAX_CYCLES_BEFORE_LEARN == 0:
            self.aprender(f"ciclo_{self.state['total_cycles']}_completo")
        
        # Guardar estado
        self._save_state()
        
        return {
            "status": "ok",
            "cycle": self.state["total_cycles"],
            "decision": decision,
            "result": result,
            "loop_detected": loop_detected
        }
