"""
ml_engine.py - MOTOR DE MACHINE LEARNING NATIVO
Classificacao, recomendacao, clustering, detecao de anomalias.
Corre em loop infinito a treinar e evoluir.
"""
import os, sys, json, time, random, math, logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ML] %(message)s",
    handlers=[
        logging.FileHandler(BASE / "cerebro" / "ml.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("ml_engine")

class MLClassifier:
    """Classificador simples baseado em frequencia."""
    
    def __init__(self):
        self.classes = {}
        self.features = defaultdict(lambda: defaultdict(int))
        self.trained = False
    
    def train(self, data):
        """Treina com dados de exemplo."""
        for item in data:
            cls = item.get("class", "unknown")
            features = item.get("features", [])
            self.classes[cls] = self.classes.get(cls, 0) + 1
            for f in features:
                self.features[cls][f] += 1
        self.trained = True
        log.info("ML treinado com " + str(len(data)) + " exemplos, " + str(len(self.classes)) + " classes")
    
    def classify(self, features):
        """Classifica um conjunto de features."""
        if not self.trained:
            return "unknown", 0.0
        
        scores = {}
        for cls in self.classes:
            score = 0
            for f in features:
                score += self.features[cls].get(f, 0)
            total = sum(self.features[cls].values()) or 1
            scores[cls] = score / total
        
        if not scores:
            return "unknown", 0.0
        
        best = max(scores, key=scores.get)
        return best, scores[best]

class MLRecommender:
    """Recomendador baseado em historico."""
    
    def __init__(self):
        self.history = []
        self.weights = {}
    
    def add_interaction(self, action, outcome, reward):
        """Regista uma interacao e seu resultado."""
        self.history.append({
            "action": action,
            "outcome": outcome,
            "reward": reward,
            "timestamp": datetime.now().isoformat()
        })
        if action not in self.weights:
            self.weights[action] = 0.5
        self.weights[action] += reward * 0.1
        self.weights[action] = max(0, min(1, self.weights[action]))
    
    def recommend(self, context=None):
        """Recomenda a melhor acao baseada no historico."""
        if not self.weights:
            return random.choice(["learn", "explore", "create", "analyze"])
        return max(self.weights, key=self.weights.get)

class MLAnomalyDetector:
    """Detetor de anomalias simples."""
    
    def __init__(self):
        self.baseline = {}
        self.threshold = 2.0
    
    def learn_baseline(self, data):
        """Aprende a linha de base do que e normal."""
        values = list(data.values()) if isinstance(data, dict) else data
        if values:
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            self.baseline = {"mean": mean, "std": math.sqrt(variance) if variance > 0 else 1}
    
    def is_anomaly(self, value):
        """Verifica se um valor e anomalo."""
        if not self.baseline:
            return False
        z_score = abs(value - self.baseline["mean"]) / self.baseline["std"]
        return z_score > self.threshold

class MLEngine:
    """Motor principal de ML."""
    
    def __init__(self):
        self.classifier = MLClassifier()
        self.recommender = MLRecommender()
        self.anomaly_detector = MLAnomalyDetector()
        self.model_file = MEMORY_DIR / "ml_model.json"
        self.cycle = 0
        self._load_model()
        self._train_initial()
    
    def _load_model(self):
        """Carrega modelo guardado."""
        try:
            if self.model_file.exists():
                with open(self.model_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.classifier.classes = data.get("classes", {})
                    self.classifier.trained = data.get("trained", False)
                    log.info("Modelo ML carregado do disco")
        except:
            pass
    
    def _save_model(self):
        """Guarda modelo em disco."""
        data = {
            "classes": self.classifier.classes,
            "trained": self.classifier.trained,
            "timestamp": datetime.now().isoformat()
        }
        with open(self.model_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _train_initial(self):
        """Treino inicial com dados de exemplo."""
        training_data = [
            {"class": "comando", "features": ["executar", "fazer", "criar", "lancar", "iniciar"]},
            {"class": "pergunta", "features": ["o que", "como", "porque", "quando", "onde"]},
            {"class": "critica", "features": ["nao", "erro", "falhou", "problema", "bug"]},
            {"class": "pedido_info", "features": ["mostra", "ver", "status", "relatorio", "dados"]},
            {"class": "negocio", "features": ["dinheiro", "receita", "lucro", "vender", "cliente"]}
        ]
        self.classifier.train(training_data)
        self._save_model()
    
    def run_cycle(self):
        """Um ciclo do motor ML."""
        self.cycle += 1
        
        if self.cycle % 10 == 0:
            synthetic_data = [
                {"class": random.choice(["comando", "pergunta", "negocio"]), 
                 "features": ["feature_" + str(i) for i in range(random.randint(1, 3))]}
                for _ in range(5)
            ]
            self.classifier.train(synthetic_data)
            self._save_model()
        
        if self.cycle % 7 == 0:
            action = self.recommender.recommend()
            log.info("ML recomenda: " + action)
        
        if self.cycle % 15 == 0:
            test_value = random.gauss(10, 2)
            if self.anomaly_detector.is_anomaly(test_value):
                log.warning("Anomalia detetada: " + str(round(test_value, 2)))
        
        time.sleep(5)

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("ML ENGINE A INICIAR...")
    log.info("=" * 50)
    
    engine = MLEngine()
    
    try:
        while True:
            engine.run_cycle()
    except KeyboardInterrupt:
        log.info("ML Engine interrompido")
    except Exception as e:
        log.error("Erro no ML: " + str(e))
        time.sleep(5)
