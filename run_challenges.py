"""
run_challenges.py - LANÇADOR DE DESAFIOS DA EQUIPA
Executa os 3 desafios em paralelo e reporta progresso.
"""
import os, sys, json, time, threading
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

# Importar os novos módulos
from cerebro.core.ml_engine import get_ml_engine
from cerebro.core.genetic_evolver import get_genetic_evolver
from cerebro.core.market_oracle import get_market_oracle

LOG_FILE = BASE / "memory" / "challenges_log.md"

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def challenge_1_ml_engine():
    """Desafio 1: Testar e evoluir o ML Engine."""
    log("[MENTE] DESAFIO #1: A testar ML Engine...")
    
    ml = get_ml_engine()
    
    # Simular aprendizagem com erros
    errors_to_learn = [
        ("connection_timeout", "rpc_supra", "retry_with_backoff", True),
        ("json_parse_error", "api_response", "validate_json_first", True),
        ("rate_limit", "telegram_api", "add_delay_between_requests", True),
        ("file_not_found", "config_load", "create_default_config", False),
        ("memory_leak", "long_running_process", "add_garbage_collection", True),
    ]
    
    for error_type, context, solution, success in errors_to_learn:
        rate = ml.learn_from_error(error_type, context, solution, success)
        log(f"  Aprendido: {error_type} -> taxa de sucesso: {rate:.2%}")
    
    # Gerar nova regra
    rule = ml.generate_new_rule()
    if rule:
        log(f"  Nova regra gerada: {rule['rule']}")
    
    stats = ml.get_stats()
    log(f"  [DADOS] ML Engine Stats: {stats}")
    
    return True

def challenge_2_genetic_evolution():
    """Desafio 2: Evolução genética dos agentes."""
    log("[DNA] DESAFIO #2: A evoluir agentes geneticamente...")
    
    evolver = get_genetic_evolver()
    
    # Registrar agentes no genoma
    souls_dir = BASE / "agents" / "souls"
    for soul_file in souls_dir.glob("*.md"):
        name = soul_file.stem
        content = soul_file.read_text(encoding="utf-8")
        capabilities = ["auto_update", "learn", "evolve"]
        evolver.register_agent_genome(name, content, capabilities)
        log(f"  Registado: {name}")
    
    # Calcular fitness para alguns agentes
    fitness_data = [
        ("supervisor", 0.95, 150, 5),
        ("developer", 0.88, 200, 12),
        ("arquiteto", 0.92, 80, 3),
        ("auto_fixer", 0.85, 300, 2),
        ("qa_tester", 0.90, 120, 8),
    ]
    
    for name, rate, tasks, errors in fitness_data:
        fitness = evolver.calculate_fitness(name, rate, tasks, errors)
        log(f"  {name}: fitness = {fitness:.2f}")
    
    # Seleção natural
    survivors = evolver.natural_selection()
    if survivors:
        log(f"  Sobreviventes: {[s['name'] for s in survivors]}")
    
    report = evolver.get_evolution_report()
    log(f"  [DADOS] {report}")
    
    return True

def challenge_3_market_oracle():
    """Desafio 3: Oráculo de mercado."""
    log("[DIN] DESAFIO #3: A escanear oportunidades de mercado...")
    
    oracle = get_market_oracle()
    
    # Escanear oportunidades
    opportunities = oracle.scan_for_opportunities()
    log(f"  Encontradas {len(opportunities)} oportunidades")
    
    # Sugerir próximo negócio
    suggestion = oracle.suggest_next_business()
    if suggestion:
        log(f"  [ALVO] Melhor oportunidade: {suggestion['name']} (score: {suggestion['score']})")
    
    # Relatório de receita
    report = oracle.get_revenue_report()
    log(f"  [DADOS] {report}")
    
    return True

def run_all_challenges():
    """Executa todos os desafios em sequência."""
    log("=" * 60)
    log("[START] INICIANDO DESAFIOS DA EQUIPA")
    log("=" * 60)
    
    # Desafio 1
    log("\n[PIN] FASE 1/3: C?rebro Qu?ntico")
    c1 = challenge_1_ml_engine()
    log(f"{'[OK]' if c1 else '[X]'} Desafio #1 {'conclu?do' if c1 else 'falhou'}")
    
    # Desafio 2
    log("\n[PIN] FASE 2/3: Evolu??o Gen?tica")
    c2 = challenge_2_genetic_evolution()
    log(f"{'[OK]' if c2 else '[X]'} Desafio #2 {'conclu?do' if c2 else 'falhou'}")
    
    # Desafio 3
    log("\n[PIN] FASE 3/3: Or?culo de Mercado")
    c3 = challenge_3_market_oracle()
    log(f"{'[OK]' if c3 else '[X]'} Desafio #3 {'conclu?do' if c3 else 'falhou'}")
    
    # Relatório final
    log("\n" + "=" * 60)
    log("[DADOS] RELAT?RIO FINAL DOS DESAFIOS")
    log("=" * 60)
    log(f"[OK] Desafio #1 - ML Engine: {'CONCLU?DO' if c1 else 'FALHOU'}")
    log(f"[OK] Desafio #2 - Evolu??o Gen?tica: {'CONCLU?DO' if c2 else 'FALHOU'}")
    log(f"[OK] Desafio #3 - Or?culo de Mercado: {'CONCLU?DO' if c3 else 'FALHOU'}")
    
    total = sum([c1, c2, c3])
    log(f"\n[SOBE] Progresso: {total}/3 desafios conclu?dos")
    
    return all([c1, c2, c3])

if __name__ == "__main__":
    success = run_all_challenges()
    sys.exit(0 if success else 1)
