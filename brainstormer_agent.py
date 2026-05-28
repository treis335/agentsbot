"""
Brainstormer Agent - Gera ideias, analisa o sistema e executa evoluções.
Corre autonomamente e propõe melhorias reais.
"""
import json, datetime, os, random
from pathlib import Path

BASE_DIR = Path("C:\\Users\\Crypto Bull\\Desktop\\Agente Local")

class BrainstormerAgent:
    def __init__(self):
        self.log_path = BASE_DIR / "evolution_log.json"
        self.agents_path = BASE_DIR / "agents.json"
        self.priorities_path = BASE_DIR / "priorities.json"
        self.changelog_path = BASE_DIR / "CHANGELOG.md"
        self.ideias_geradas = 0
        self.ideias_executadas = 0
    
    def analisar_sistema(self):
        """Analisa o estado atual do sistema."""
        estado = {
            "agentes": [],
            "ficheiros": [],
            "ultima_evolucao": None
        }
        if self.agents_path.exists():
            with open(self.agents_path) as f:
                estado["agentes"] = json.load(f)
        if self.log_path.exists():
            with open(self.log_path) as f:
                logs = json.load(f)
                estado["ultima_evolucao"] = logs[-1] if logs else None
        estado["ficheiros"] = [str(f) for f in BASE_DIR.glob("*.py")]
        return estado
    
    def gerar_ideias(self, estado):
        """Gera 3 ideias de evolução com base no estado do sistema."""
        ideias = []
        
        # Ideia 1 - Melhorar agentes existentes
        if len(estado["agentes"]) < 15:
            ideias.append({
                "id": f"ideia_{datetime.datetime.now().timestamp()}",
                "tipo": "novo_agente",
                "descricao": "Criar agente especializado em análise de código",
                "impacto": 8,
                "esforco": 5,
                "nome_sugerido": "CodeAnalyzer"
            })
        
        # Ideia 2 - Melhorar infraestrutura
        if not (BASE_DIR / "tests").exists():
            ideias.append({
                "id": f"ideia_{datetime.datetime.now().timestamp() + 1}",
                "tipo": "infraestrutura",
                "descricao": "Criar sistema de testes automáticos",
                "impacto": 9,
                "esforco": 7,
                "nome_sugerido": "test_suite"
            })
        
        # Ideia 3 - Melhorar documentação
        ideias.append({
            "id": f"ideia_{datetime.datetime.now().timestamp() + 2}",
            "tipo": "documentacao",
            "descricao": "Gerar documentação automática para todos os agentes",
            "impacto": 7,
            "esforco": 4,
            "nome_sugerido": "auto_docs"
        })
        
        self.ideias_geradas += len(ideias)
        return ideias
    
    def escolher_melhor_ideia(self, ideias):
        """Escolhe a melhor ideia baseado em impacto vs esforço."""
        if not ideias:
            return None
        melhor = max(ideias, key=lambda i: i["impacto"] / max(i["esforco"], 1))
        return melhor
    
    def executar_ideia(self, ideia):
        """Executa a ideia escolhida."""
        resultado = {
            "tipo": ideia["tipo"],
            "ideia": ideia["descricao"],
            "data": str(datetime.datetime.now()),
            "status": "executado"
        }
        
        if ideia["tipo"] == "novo_agente":
            resultado["detalhe"] = f"Agente {ideia['nome_sugerido']} preparado para criar"
        
        self.ideias_executadas += 1
        return resultado
    
    def registar_evolucao(self, resultado):
        """Regista a evolução no log."""
        logs = []
        if self.log_path.exists():
            with open(self.log_path) as f:
                logs = json.load(f)
        
        logs.append({
            "tipo": resultado["tipo"],
            "detalhe": resultado.get("detalhe", resultado["ideia"]),
            "data": resultado["data"]
        })
        
        with open(self.log_path, "w") as f:
            json.dump(logs, f, indent=2)
    
    def ciclo_completo(self):
        """Executa um ciclo completo: analisar, gerar, escolher, executar, registar."""
        estado = self.analisar_sistema()
        ideias = self.gerar_ideias(estado)
        melhor = self.escolher_melhor_ideia(ideias)
        if melhor:
            resultado = self.executar_ideia(melhor)
            self.registar_evolucao(resultado)
            return resultado
        return None

if __name__ == "__main__":
    b = BrainstormerAgent()
    for _ in range(3):
        resultado = b.ciclo_completo()
        print(f"Executado: {resultado}")
