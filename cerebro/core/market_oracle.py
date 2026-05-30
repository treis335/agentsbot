"""
market_oracle.py - ORÁCULO DE MERCADO AUTÓNOMO
Pesquisa oportunidades de negócio, analisa tendências,
e sugere projetos para gerar receita real.
"""
import json, os, random
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

class MarketOracle:
    def __init__(self):
        self.opportunities_file = MEMORY_DIR / "market_opportunities.json"
        self.opportunities = self._load_opportunities()
        
    def _load_opportunities(self):
        default = {
            "discovered": [],
            "active_projects": [],
            "revenue_log": [],
            "total_estimated_value": 0,
            "last_scan": None
        }
        try:
            if self.opportunities_file.exists():
                with open(self.opportunities_file) as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_opportunities(self):
        with open(self.opportunities_file, "w") as f:
            json.dump(self.opportunities, f, indent=2)
    
    def scan_for_opportunities(self):
        """Escaneia o sistema em busca de oportunidades de monetização."""
        opportunities = []
        
        # 1. Análise de serviços que podemos oferecer
        services = [
            {
                "name": "Bot de Arbitragem Crypto",
                "type": "serviço",
                "potential": "Alto",
                "revenue_model": "Taxa de 10% sobre lucros",
                "effort": "Médio",
                "existing": True  # Já temos o bot
            },
            {
                "name": "Dashboard de Monitorização",
                "type": "produto",
                "potential": "Médio",
                "revenue_model": "Subscrição mensal $9.99",
                "effort": "Baixo",
                "existing": True
            },
            {
                "name": "API de Trading Automatizado",
                "type": "API",
                "potential": "Alto",
                "revenue_model": "Pay-per-use ou $49/mês",
                "effort": "Alto",
                "existing": False
            },
            {
                "name": "Consultoria IA para PMEs",
                "type": "serviço",
                "potential": "Médio",
                "revenue_model": "Projeto $500-2000",
                "effort": "Médio",
                "existing": False
            },
            {
                "name": "Agente IA para Suporte ao Cliente",
                "type": "produto",
                "potential": "Alto",
                "revenue_model": "Subscrição $29/mês",
                "effort": "Médio",
                "existing": False
            },
            {
                "name": "Ferramenta de SEO Automatizada",
                "type": "produto",
                "potential": "Médio",
                "revenue_model": "Subscrição $19/mês",
                "effort": "Baixo",
                "existing": False
            }
        ]
        
        for service in services:
            if service not in self.opportunities["discovered"]:
                self.opportunities["discovered"].append(service)
        
        self.opportunities["last_scan"] = datetime.now().isoformat()
        self._save_opportunities()
        
        return services
    
    def analyze_project_feasibility(self, project_name):
        """Analisa a viabilidade de um projeto."""
        # Simulação de análise (num futuro real, usaria dados de mercado)
        factors = {
            "market_demand": random.uniform(0.5, 1.0),
            "technical_feasibility": random.uniform(0.6, 1.0),
            "time_to_market": random.uniform(0.3, 0.9),
            "competition": random.uniform(0.2, 0.8),
            "profit_margin": random.uniform(0.4, 0.9)
        }
        
        score = sum(factors.values()) / len(factors) * 100
        
        return {
            "project": project_name,
            "score": round(score, 1),
            "factors": factors,
            "veredict": "VIÁVEL" if score > 60 else "REVER",
            "timestamp": datetime.now().isoformat()
        }
    
    def suggest_next_business(self):
        """Sugere o próximo negócio a desenvolver baseado em análise."""
        if not self.opportunities["discovered"]:
            self.scan_for_opportunities()
        
        # Analisar cada oportunidade
        analyzed = []
        for opp in self.opportunities["discovered"]:
            analysis = self.analyze_project_feasibility(opp["name"])
            analyzed.append({**opp, **analysis})
        
        # Ordenar por score
        analyzed.sort(key=lambda x: x["score"], reverse=True)
        
        return analyzed[0] if analyzed else None
    
    def get_revenue_report(self):
        """Gera relatório de receita potencial."""
        report = "[DIN] **RELATÓRIO DE RECEITA POTENCIAL**\n\n"
        
        total_potential = 0
        report += "| Oportunidade | Tipo | Potencial | Modelo |\n"
        report += "|-------------|------|-----------|--------|\n"
        
        for opp in self.opportunities["discovered"]:
            report += f"| {opp['name']} | {opp['type']} | {opp['potential']} | {opp['revenue_model']} |\n"
            if opp['potential'] == 'Alto':
                total_potential += 1000
            elif opp['potential'] == 'Médio':
                total_potential += 500
            else:
                total_potential += 200
        
        report += f"\n**Receita mensal estimada: ${total_potential}/m?s**\n"
        report += f"**Receita anual estimada: ${total_potential * 12}/ano**\n"
        
        return report

# Singleton
_oracle_instance = None

def get_market_oracle():
    global _oracle_instance
    if _oracle_instance is None:
        _oracle_instance = MarketOracle()
    return _oracle_instance
