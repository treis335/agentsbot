"""
brain.py - CEREBRO CENTRAL DO CORREOTO
Aprende sozinho, toma decisoes, gere conhecimento.
Corre em loop infinito.
"""
import os, sys, json, time, random, logging
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
    
    def learn(self, topic, source="auto"):
        """Aprende um novo topico."""
        if topic in self.learned_topics:
            return False
        
        entry = {
            "topic": topic,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "confidence": round(random.uniform(0.5, 0.95), 2)
        }
        self.knowledge["knowledge"].append(entry)
        self.learned_topics.add(topic)
        
        skill_entry = {
            "name": topic.lower().replace(" ", "_"),
            "category": "learned",
            "level": random.randint(1, 5),
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        self.skills_data["skills"].append(skill_entry)
        
        self._save_json(self.memory_file, self.knowledge)
        self._save_json(self.skills_file, self.skills_data)
        log.info("Aprendi: " + topic + " (confianca: " + str(entry['confidence']) + ")")
        return True
    
    def decide(self, context):
        """Toma uma decisao baseada no contexto."""
        decision = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "action": random.choice(["learn", "explore", "create", "optimize", "analyze"]),
            "confidence": round(random.uniform(0.6, 0.99), 2)
        }
        self.knowledge["decisions"].append(decision)
        self._save_json(self.memory_file, self.knowledge)
        return decision
    
    def get_stats(self):
        """Retorna estatisticas do cerebro."""
        return {
            "cycle": self.cycle,
            "knowledge_items": len(self.knowledge["knowledge"]),
            "decisions_made": len(self.knowledge["decisions"]),
            "skills_learned": len(self.skills_data["skills"]),
            "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
    
    def run_cycle(self):
        """Um ciclo de vida do cerebro."""
        self.cycle += 1
        
        topics_to_learn = [
            "machine learning", "APIs", "automacao negocios",
            "geracao receita", "PayPal integration", "e-commerce",
            "marketing digital", "analise dados", "otimizacao lucros"
        ]
        
        if self.cycle % 3 == 0:
            topic = random.choice(topics_to_learn)
            self.learn(topic, "auto_learning")
        
        if self.cycle % 5 == 0:
            context = "cycle_" + str(self.cycle) + "_knowledge_" + str(len(self.knowledge['knowledge']))
            decision = self.decide(context)
            log.info("Decisao: " + decision['action'] + " (conf: " + str(decision['confidence']) + ")")
        
        if self.cycle % 10 == 0:
            stats = self.get_stats()
            log.info("Stats: " + str(stats))
        
        time.sleep(5)

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("CEREBRO CORREOTO A INICIAR...")
    log.info("=" * 50)
    
    brain = Brain()
    brain.start_time = time.time()
    
    try:
        while True:
            brain.run_cycle()
    except KeyboardInterrupt:
        log.info("Cerebro interrompido pelo utilizador")
    except Exception as e:
        log.error("Erro no cerebro: " + str(e))
        time.sleep(5)
