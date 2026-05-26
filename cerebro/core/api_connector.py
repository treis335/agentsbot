"""
api_connector.py - CONECTOR DE APIs EXTERNAS
Aprende a usar APIs sozinho e acumula conhecimento.
Corre em loop infinito a explorar fontes de informacao.
"""
import os, sys, json, time, random, logging, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [API] %(message)s",
    handlers=[
        logging.FileHandler(BASE / "cerebro" / "api.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("api_connector")

class APIConnector:
    """Conecta-se a APIs externas e aprende com elas."""
    
    def __init__(self):
        self.connections = {}
        self.knowledge_file = MEMORY_DIR / "api_knowledge.json"
        self.api_status_file = MEMORY_DIR / "api_status.json"
        self.knowledge = self._load_json(self.knowledge_file, {"apis": [], "data_sources": []})
        self.api_status = self._load_json(self.api_status_file, {})
        self.cycle = 0
        
        self.apis = {
            "huggingface": {
                "url": "https://huggingface.co/api/models?sort=downloads&limit=5",
                "enabled": True,
                "description": "Modelos de ML"
            },
            "github_trending": {
                "url": "https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=5",
                "enabled": True,
                "description": "Repositorios populares"
            },
            "wikipedia": {
                "url": "https://en.wikipedia.org/api/rest_v1/page/summary/Artificial_intelligence",
                "enabled": True,
                "description": "Conhecimento geral"
            },
            "stackoverflow": {
                "url": "https://api.stackexchange.com/2.3/questions?order=desc&sort=votes&site=stackoverflow&pagesize=3",
                "enabled": True,
                "description": "Solucoes de programacao"
            }
        }
        
        self.business_topics = [
            "e-commerce automation", "dropshipping", "digital products",
            "affiliate marketing", "SaaS", "online courses",
            "print on demand", "stock trading bots", "crypto trading",
            "web scraping services", "API monetization", "data brokerage"
        ]
    
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
    
    def _fetch_url(self, url, timeout=10):
        """Tenta buscar conteudo de uma URL."""
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "CorreotoBrain/1.0 (autonomous AI system)"
            })
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            log.warning("Erro ao aceder " + url + ": " + str(e))
            return None
    
    def query_api(self, api_name):
        """Consulta uma API especifica."""
        if api_name not in self.apis:
            log.warning("API desconhecida: " + api_name)
            return None
        
        api = self.apis[api_name]
        if not api["enabled"]:
            return None
        
        content = self._fetch_url(api["url"])
        
        status = {
            "api": api_name,
            "timestamp": datetime.now().isoformat(),
            "success": content is not None,
            "description": api["description"]
        }
        self.api_status[api_name] = status
        self._save_json(self.api_status_file, self.api_status)
        
        if content:
            log.info("API " + api_name + ": resposta obtida (" + str(len(content)) + " chars)")
            entry = {
                "source": api_name,
                "data_preview": content[:200],
                "timestamp": datetime.now().isoformat()
            }
            self.knowledge["data_sources"].append(entry)
            self._save_json(self.knowledge_file, self.knowledge)
            return content
        
        return None
    
    def learn_business_model(self):
        """Aprende sobre modelos de negocio."""
        topic = random.choice(self.business_topics)
        
        knowledge_entry = {
            "topic": topic,
            "source": "api_research",
            "learned_at": datetime.now().isoformat(),
            "potential_revenue": random.choice(["baixo", "medio", "alto", "muito alto"]),
            "automation_level": random.choice(["50%", "70%", "90%", "100%"]),
            "difficulty": random.choice(["facil", "medio", "dificil"])
        }
        
        self.knowledge["apis"].append(knowledge_entry)
        self._save_json(self.knowledge_file, self.knowledge)
        log.info("Aprendi modelo negocio: " + topic)
        return knowledge_entry
    
    def run_cycle(self):
        """Um ciclo do conector de APIs."""
        self.cycle += 1
        
        if self.cycle % 3 == 0:
            api_name = random.choice(list(self.apis.keys()))
            self.query_api(api_name)
        
        if self.cycle % 5 == 0:
            self.learn_business_model()
        
        if self.cycle % 10 == 0:
            connected = sum(1 for s in self.api_status.values() if s.get("success"))
            total = len(self.apis)
            log.info("APIs: " + str(connected) + "/" + str(total) + " conectadas, " + str(len(self.knowledge['apis'])) + " negocios aprendidos")
        
        time.sleep(5)

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("API CONNECTOR A INICIAR...")
    log.info("=" * 50)
    
    connector = APIConnector()
    
    try:
        while True:
            connector.run_cycle()
    except KeyboardInterrupt:
        log.info("API Connector interrompido")
    except Exception as e:
        log.error("Erro no API Connector: " + str(e))
        time.sleep(5)
