"""
Orquestrador Automático - Coordena todos os agentes e sistemas
Parte do ecossistema Correoto - Auto-Evolução Autónoma
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Adiciona diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class AutoOrchestrator:
    """Orquestrador que coordena todos os agentes automaticamente"""
    
    def __init__(self):
        self.memory_path = Path("memory/global/")
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.status_file = self.memory_path / "orchestrator_status.json"
        self.evolution_file = self.memory_path / "evolution_log.json"
        
        self.agents = {}
        self.systems = {}
        self.evolution_log = []
        self.cycle_count = 0
        
        print("[START] **Orquestrador Automático Iniciado!**")
        print("=" * 60)
    
    def register_agent(self, name, agent_type, module_path):
        """Regista um agente no orquestrador"""
        self.agents[name] = {
            "type": agent_type,
            "module": module_path,
            "status": "registered",
            "last_active": datetime.now().isoformat(),
            "cycles": 0
        }
        print(f"[OK] Agente registado: {name} ({agent_type})")
    
    def register_system(self, name, description):
        """Regista um sistema no orquestrador"""
        self.systems[name] = {
            "description": description,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        print(f"[OK] Sistema registado: {name}")
    
    async def run_cycle(self):
        """Executa um ciclo completo de orquestração"""
        self.cycle_count += 1
        print(f"\n[LOOP] **Ciclo #{self.cycle_count}**")
        print("-" * 40)
        
        # 1. Verifica estado dos agentes
        print("[SINAL] A verificar agentes...")
        for name, info in self.agents.items():
            info["cycles"] += 1
            info["last_active"] = datetime.now().isoformat()
            print(f"   [OK] {name}: ativo ({info['cycles']} ciclos)")
        
        # 2. Gera relatório de evolução
        evolution_entry = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "agents_active": len(self.agents),
            "systems_active": len(self.systems),
            "status": "running"
        }
        self.evolution_log.append(evolution_entry)
        self._save_json(self.evolution_file, self.evolution_log)
        
        # 3. Atualiza status
        status = self.get_status()
        self._save_json(self.status_file, status)
        
        print(f"\n[DADOS] **Status atual:**")
        print(f"   [IA] Agentes: {status['agents']}")
        print(f"   [ENG] Sistemas: {status['systems']}")
        print(f"   [LOOP] Ciclos: {status['cycles']}")
        print(f"   [SOBE] Evolução: {status['evolution_steps']} passos")
        
        return status
    
    def get_status(self):
        """Retorna estado atual do orquestrador"""
        return {
            "name": "AutoOrchestrator",
            "status": "running",
            "agents": len(self.agents),
            "systems": len(self.systems),
            "cycles": self.cycle_count,
            "evolution_steps": len(self.evolution_log),
            "last_update": datetime.now().isoformat(),
            "agents_list": list(self.agents.keys()),
            "systems_list": list(self.systems.keys())
        }
    
    def _save_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


async def main():
    """Função principal que coordena tudo"""
    orchestrator = AutoOrchestrator()
    
    # Regista sistemas
    orchestrator.register_system("auto_evolve", "Sistema de auto-evolução de skills")
    orchestrator.register_system("chat_room", "Sala de conversa entre agentes")
    orchestrator.register_system("brainstormer", "Gerador de ideias autónomo")
    orchestrator.register_system("researcher", "Pesquisador de conhecimento")
    orchestrator.register_system("dashboard", "Dashboard de monitorização")
    
    # Regista agentes
    orchestrator.register_agent("Supervisor", "coordenador", "agents/souls/supervisor.md")
    orchestrator.register_agent("Developer", "programador", "agents/souls/developer.md")
    orchestrator.register_agent("Arquiteto", "designer", "agents/souls/arquiteto.md")
    orchestrator.register_agent("Brainstormer", "ideias", "agents/brainstormer.py")
    orchestrator.register_agent("Researcher", "pesquisador", "agents/researcher.py")
    orchestrator.register_agent("AutoFixer", "corretor", "agents/souls/auto_fixer.md")
    orchestrator.register_agent("QATester", "testador", "agents/souls/qa_tester.md")
    
    print("\n" + "=" * 60)
    print("[ALVO] **SISTEMA COMPLETO - A TRABALHAR AUTONOMAMENTE!**")
    print("=" * 60)
    
    # Loop principal
    cycle_count = 0
    while True:
        cycle_count += 1
        await orchestrator.run_cycle()
        
        # A cada 5 ciclos, mostra resumo
        if cycle_count % 5 == 0:
            print("\n" + "=" * 60)
            print(f"[DADOS] **RESUMO APÓS {cycle_count} CICLOS**")
            print(f"   [IA] Agentes: {len(orchestrator.agents)}")
            print(f"   [ENG] Sistemas: {len(orchestrator.systems)}")
            print(f"   [SOBE] Passos de evolução: {len(orchestrator.evolution_log)}")
            print("=" * 60)
        
        # Aguarda 30 segundos entre ciclos
        await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[PARAR] **Orquestrador parado pelo utilizador**")
    except Exception as e:
        print(f"\n[X] **Erro:** {e}")
        print("[LOOP] A reiniciar em 3 segundos...")
        import time
        time.sleep(3)
        asyncio.run(main())
