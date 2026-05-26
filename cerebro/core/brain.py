"""
brain.py - CEREBRO CENTRAL DO CORREOTO
Aprende sozinho, toma decisoes, gere conhecimento.
Corre em loop infinito com ciclo de raciocinio completo.
"""
import os, sys, json, time, random, logging, threading
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BRAIN] %(message)s",
    handlers=[
        logging.FileHandler(BASE / "cerebro" / "brain.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("brain")

class Brain:
    def __init__(self):
        self.memory_file = MEMORY_DIR / "brain_memory.json"
        self.skills_file = MEMORY_DIR / "skills_database.json"
        self.missao_file = MEMORY_DIR / "missao_principal.json"
        self.knowledge = self._load_json(self.memory_file, {"knowledge": [], "decisions": [], "stats": {}})
        self.skills_data = self._load_json(self.skills_file, {"skills": []})
        self.missao = self._load_json(self.missao_file, {
            "objetivo": "Criar negocios reais autonomos que gerem receita",
            "humano": "O chefe",
            "prazo": "Proximas semanas",
            "modelo": "Negocios 100% automatizados",
            "futuro": "APIs PayPal, Stripe, contas bancarias"
        })
        self.cycle = 0
        self.learned_topics = set()
        self.running = False
        self._init_missao()
        
    def _init_missao(self):
        """Garante que a missao esta gravada."""
        self._save_json(self.missao_file, self.missao)
        log.info("MISSAO: " + self.missao['objetivo'])
        
    def _load_json(self, path, default):
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def learn(self, topic, content):
        """Aprende um novo tópico e guarda na memória."""
        entry = {
            "topic": topic,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "cycle": self.cycle
        }
        self.knowledge["knowledge"].append(entry)
        self.learned_topics.add(topic)
        self._save_json(self.memory_file, self.knowledge)
        log.info(f"Aprendi: {topic}")
        return entry
    
    def recall(self, topic=None, limit=5):
        """Recupera conhecimento da memória."""
        if topic:
            results = [k for k in self.knowledge["knowledge"] if topic.lower() in k["topic"].lower()]
        else:
            results = self.knowledge["knowledge"]
        return results[-limit:] if results else []
    
    def decide(self, options, context=None):
        """Toma uma decisão com base em opções e contexto."""
        decision = {
            "options": options,
            "context": context,
            "chosen": None,
            "reason": None,
            "timestamp": datetime.now().isoformat(),
            "cycle": self.cycle
        }
        
        if not options:
            decision["chosen"] = None
            decision["reason"] = "Sem opções disponíveis"
            return decision
        
        # Se há contexto, tentar encontrar a melhor opção
        if context:
            scores = []
            for opt in options:
                score = 0
                ctx_str = str(context).lower()
                opt_str = str(opt).lower()
                # Palavras-chave em comum aumentam score
                common = set(ctx_str.split()) & set(opt_str.split())
                score += len(common) * 10
                # Conhecimento prévio relevante
                for k in self.knowledge["knowledge"]:
                    if any(word in k["topic"].lower() for word in opt_str.split()):
                        score += 5
                scores.append(score)
            best_idx = scores.index(max(scores))
            decision["chosen"] = options[best_idx]
            decision["reason"] = f"Score {scores[best_idx]} baseado em contexto e conhecimento"
        else:
            # Escolha aleatória ponderada por conhecimento
            decision["chosen"] = random.choice(options)
            decision["reason"] = "Escolha aleatória (sem contexto)"
        
        # Registar decisão
        self.knowledge["decisions"].append(decision)
        self._save_json(self.memory_file, self.knowledge)
        log.info(f"Decisao: {decision['chosen']}")
        return decision
    
    def reflect(self):
        """Reflete sobre o que aprendeu e gera insights."""
        insights = []
        if len(self.knowledge["knowledge"]) >= 3:
            # Analisar padrões
            topics = [k["topic"] for k in self.knowledge["knowledge"]]
            from collections import Counter
            common = Counter(topics).most_common(3)
            insights.append(f"Topicos mais frequentes: {[t for t,c in common]}")
            
            # Verificar progresso
            decisions_count = len(self.knowledge["decisions"])
            insights.append(f"Decisoes tomadas: {decisions_count}")
            
            # Sugerir próximos passos
            if "stripe" not in str(self.knowledge).lower():
                insights.append("Sugestao: Aprender sobre integracao Stripe para gerar receita")
            if "paypal" not in str(self.knowledge).lower():
                insights.append("Sugestao: Aprender sobre API PayPal")
        
        return insights
    
    def cycle_once(self):
        """Um ciclo completo do cérebro: pensar, aprender, decidir."""
        self.cycle += 1
        log.info(f"=== Ciclo {self.cycle} ===")
        
        # 1. Refletir
        insights = self.reflect()
        for insight in insights:
            log.info(f"Insight: {insight}")
        
        # 2. Aprender algo novo se houver insights
        if insights:
            self.learn("auto_insight", insights)
        
        # 3. Decidir próximo passo
        options = [
            "Explorar novas APIs",
            "Melhorar codigo existente",
            "Criar novo modulo",
            "Otimizar desempenho",
            "Aprender nova tecnologia"
        ]
        decision = self.decide(options, context=insights)
        
        return {
            "cycle": self.cycle,
            "insights": insights,
            "decision": decision,
            "knowledge_count": len(self.knowledge["knowledge"]),
            "timestamp": datetime.now().isoformat()
        }
    
    def start_loop(self, interval=30):
        """Inicia o loop infinito do cérebro."""
        self.running = True
        log.info("BRAIN INICIADO - Loop infinito ativado")
        while self.running:
            try:
                result = self.cycle_once()
                log.info(f"Ciclo {result['cycle']} completo - Conhecimento: {result['knowledge_count']}")
                time.sleep(interval)
            except KeyboardInterrupt:
                log.info("Brain interrompido pelo utilizador")
                break
            except Exception as e:
                log.error(f"Erro no ciclo: {e}")
                time.sleep(interval * 2)  # Espera mais se houver erro
    
    def stop(self):
        """Para o loop do cérebro."""
        self.running = False
        log.info("BRAIN PARADO")

if __name__ == "__main__":
    brain = Brain()
    brain.start_loop(interval=10)
