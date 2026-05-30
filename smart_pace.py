"""
Smart Pace System v1.0 - Controlo de Ritmo Inteligente
=====================================================
Estratégia: Em vez de iterar rápido e atingir o limite,
cada iteração faz MAIS trabalho de forma mais LENTA e PROFUNDA.

Como funciona:
1. Monitoriza o número de iterações usadas
2. Se estiver perto do limite -> desacelera e faz deep work
3. Cada iteração: pesquisa + analisa + executa + testa (tudo de uma vez)
4. Modo "Deep Work" ativado automaticamente quando necessário
"""

import os
import time
import json
import sys
from datetime import datetime

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Configuração ---------------------------------------------------------
SMART_PACE_FILE = "smart_pace.flg"
ITERATION_LOG = "iteration_log.json"
MAX_ITERATIONS_BEFORE_SLOW = 15  # Começa a desacelerar após 15 iterações
MAX_ITERATIONS_HARD_LIMIT = 25   # Limite duro (antes do sistema nos parar)
DEEP_WORK_THRESHOLD = 20         # Ativa deep work mode

# Estado global
state = {
    "iteration_count": 0,
    "deep_work_mode": False,
    "slow_mode": False,
    "last_reset": datetime.now().isoformat(),
    "pace_factor": 1.0,  # 1.0 = normal, 2.0 = 2x mais lento
    "tasks_per_iteration": 1,  # Quantas tarefas por iteração
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SMART_PACE] [{ts}] {msg}", flush=True)

def load_state():
    """Carrega estado do ficheiro"""
    global state
    try:
        if os.path.exists(SMART_PACE_FILE):
            with open(SMART_PACE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                state.update(data)
                log(f"Estado carregado: {state['iteration_count']} iterações")
    except Exception as e:
        log(f"Erro ao carregar estado: {e}")

def save_state():
    """Salva estado para ficheiro"""
    try:
        with open(SMART_PACE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"Erro ao salvar estado: {e}")

def increment_iteration():
    """Incrementa contador de iterações e ajusta ritmo"""
    state["iteration_count"] += 1
    count = state["iteration_count"]
    
    # Ajusta ritmo baseado no número de iterações
    if count >= DEEP_WORK_THRESHOLD:
        state["deep_work_mode"] = True
        state["slow_mode"] = True
        state["pace_factor"] = 3.0
        state["tasks_per_iteration"] = 5
        log(f"[!] DEEP WORK MODE ATIVADO! ({count} iterações)")
        log(f"   -> Pace factor: {state['pace_factor']}x")
        log(f"   -> Tarefas por iteração: {state['tasks_per_iteration']}")
    elif count >= MAX_ITERATIONS_BEFORE_SLOW:
        state["slow_mode"] = True
        state["pace_factor"] = 2.0
        state["tasks_per_iteration"] = 3
        log(f"[!] SLOW MODE ATIVADO! ({count} iterações)")
        log(f"   -> Pace factor: {state['pace_factor']}x")
    
    # Se estiver muito perto do limite, avisa
    if count >= MAX_ITERATIONS_HARD_LIMIT - 5:
        log(f"[ALARME] PERTO DO LIMITE! ({count}/{MAX_ITERATIONS_HARD_LIMIT})")
        log(f"   -> A preparar reset automático...")
    
    save_state()
    return count

def reset_counter():
    """Reseta o contador (quando o sistema reinicia)"""
    old_count = state["iteration_count"]
    state["iteration_count"] = 0
    state["deep_work_mode"] = False
    state["slow_mode"] = False
    state["pace_factor"] = 1.0
    state["tasks_per_iteration"] = 1
    state["last_reset"] = datetime.now().isoformat()
    save_state()
    log(f"[LOOP] Contador resetado! (estava em {old_count})")
    return True

def get_pace_delay():
    """Devolve o delay recomendado entre ações (em segundos)"""
    base_delay = 0.5  # 500ms base
    return base_delay * state["pace_factor"]

def should_do_deep_work():
    """Deve fazer deep work? (várias tarefas de uma vez)"""
    return state["deep_work_mode"]

def get_tasks_per_iteration():
    """Quantas tarefas fazer por iteração"""
    return state["tasks_per_iteration"]

def get_status():
    """Devolve status atual para debugging"""
    return {
        "iteration_count": state["iteration_count"],
        "deep_work_mode": state["deep_work_mode"],
        "slow_mode": state["slow_mode"],
        "pace_factor": state["pace_factor"],
        "tasks_per_iteration": state["tasks_per_iteration"],
        "last_reset": state["last_reset"],
        "max_iterations_before_slow": MAX_ITERATIONS_BEFORE_SLOW,
        "max_iterations_hard_limit": MAX_ITERATIONS_HARD_LIMIT,
        "deep_work_threshold": DEEP_WORK_THRESHOLD,
    }

def log_iteration(action, details=""):
    """Regista iteração no log"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "iteration": state["iteration_count"],
        "action": action,
        "details": details,
        "mode": "deep_work" if state["deep_work_mode"] else ("slow" if state["slow_mode"] else "normal")
    }
    
    try:
        logs = []
        if os.path.exists(ITERATION_LOG):
            with open(ITERATION_LOG, "r", encoding="utf-8") as f:
                logs = json.load(f)
        
        logs.append(entry)
        
        # Mantém apenas últimos 100 logs
        if len(logs) > 100:
            logs = logs[-100:]
        
        with open(ITERATION_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"Erro ao registar iteração: {e}")

# --- Inicialização --------------------------------------------------------
load_state()
log(f"Smart Pace System iniciado!")
log(f"  -> Iterações atuais: {state['iteration_count']}")
log(f"  -> Modo: {'DEEP WORK' if state['deep_work_mode'] else ('SLOW' if state['slow_mode'] else 'NORMAL')}")
log(f"  -> Pace factor: {state['pace_factor']}x")

if __name__ == "__main__":
    # Teste rápido
    print("\n=== SMART PACE SYSTEM - TEST ===")
    print(json.dumps(get_status(), indent=2, ensure_ascii=False))
    print("\nA simular iterações...")
    for i in range(5):
        increment_iteration()
        print(f"  Iteração {state['iteration_count']}: delay={get_pace_delay():.1f}s, tasks={get_tasks_per_iteration()}")
        time.sleep(0.1)
    print("\nStatus final:")
    print(json.dumps(get_status(), indent=2, ensure_ascii=False))
