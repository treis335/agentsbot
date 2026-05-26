"""
ml_engine.py — MOTOR DE APRENDIZAGEM AUTÓNOMA DO CORREOTO
Aprende padrões, classifica informação e faz recomendações baseadas em experiência.
Usa ML leve (sem dependências pesadas) para funcionar 100% local.
"""
import json, time, logging, random, math
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ML] %(message)s")
log = logging.getLogger("ml_engine")


class MLClassifier:
    """Classificador simples baseado em frequência de palavras-chave.
    Aprende padrões e classifica texto em categorias."""
    
    def __init__(self):
        self.model_file = MEMORY_DIR / "ml_classifier_model.json"
        self.model = self._load_json(self.model_file, {
            "categories": {},
            "word_freq": {},
            "total_trained": 0
        })
        self.cycle = 0
    
    def _load_json(self, path, default):
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except: pass
        return default
    
    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _extract_features(self, text):
        """Extrai palavras-chave como features."""
        words = text.lower().split()
        # Filtrar palavras curtas e comuns
        stopwords = {"o", "a", "os", "as", "um", "uma", "de", "da", "do", "em", "para", 
                     "com", "por", "que", "é", "não", "se", "mais", "como", "dos", "das"}
        return [w for w in words if len(w) > 3 and w not in stopwords]
    
    def train(self, text, category):
        """Treina o classificador com um exemplo."""
        self.cycle += 1
        features = self._extract_features(text)
        
        if category not in self.model["categories"]:
            self.model["categories"][category] = 0
        
        self.model["categories"][category] += 1
        
        for word in features:
            if word not in self.model["word_freq"]:
                self.model["word_freq"][word] = {}
            if category not in self.model["word_freq"][word]:
                self.model["word_freq"][word][category] = 0
            self.model["word_freq"][word][category] += 1
        
        self.model["total_trained"] += 1
        self._save_json(self.model_file, self.model)
        log.info(f"Treinado: '{text[:30]}...' -> {category}")
    
    def classify(self, text):
        """Classifica um texto numa categoria."""
        features = self._extract_features(text)
        if not features or not self.model["categories"]:
            return {"category": "desconhecido", "confidence": 0.0}
        
        scores = {}
        total_cats = sum(self.model["categories"].values())
        
        for category in self.model["categories"]:
            # Prior probability
            prior = self.model["categories"][category] / total_cats
            # Likelihood
            likelihood = 1.0
            for word in features:
                word_data = self.model["word_freq"].get(word, {})
                freq_in_cat = word_data.get(category, 0)
                total_word = sum(word_data.values()) if word_data else 1
                # Laplace smoothing
                prob = (freq_in_cat + 1) / (total_word + len(self.model["categories"]))
                likelihood *= prob
            
            scores[category] = prior * likelihood
        
        # Normalizar
        total_score = sum(scores.values()) or 1
        for cat in scores:
            scores[cat] /= total_score
        
        best_cat = max(scores, key=scores.get)
        return {
            "category": best_cat,
            "confidence": scores[best_cat],
            "all_scores": scores
        }
    
    def get_stats(self):
        return {
            "total_trained": self.model["total_trained"],
            "categories": list(self.model["categories"].keys()),
            "vocabulary_size": len(self.model["word_freq"])
        }


class MLRecommender:
    """Sistema de recomendação baseado em histórico de decisões.
    Aprende o que funciona melhor e recomenda ações futuras."""
    
    def __init__(self):
        self.model_file = MEMORY_DIR / "ml_recommender_model.json"
        self.model = self._load_json(self.model_file, {
            "action_history": [],
            "action_scores": {},
            "context_patterns": []
        })
        self.cycle = 0
    
    def _load_json(self, path, default):
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except: pass
        return default
    
    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def record_action(self, action, context, outcome_score=0.5):
        """Regista uma ação e o seu resultado."""
        self.cycle += 1
        record = {
            "action": action,
            "context": context,
            "outcome_score": outcome_score,
            "timestamp": datetime.now().isoformat(),
            "cycle": self.cycle
        }
        self.model["action_history"].append(record)
        
        # Atualizar score da ação
        if action not in self.model["action_scores"]:
            self.model["action_scores"][action] = []
        self.model["action_scores"][action].append(outcome_score)
        
        # Manter apenas últimos 1000 registos
        if len(self.model["action_history"]) > 1000:
            self.model["action_history"] = self.model["action_history"][-1000:]
        
        self._save_json(self.model_file, self.model)
        log.info(f"Ação registada: {action} (score: {outcome_score})")
    
    def recommend(self, context=None, top_n=3):
        """Recomenda as melhores ações com base no histórico."""
        if not self.model["action_scores"]:
            return []
        
        avg_scores = {}
        for action, scores in self.model["action_scores"].items():
            avg_scores[action] = sum(scores) / len(scores)
        
        # Ordenar por score médio
        sorted_actions = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for action, score in sorted_actions[:top_n]:
            recommendations.append({
                "action": action,
                "avg_score": round(score, 3),
                "times_tried": len(self.model["action_scores"][action])
            })
        
        return recommendations
    
    def get_stats(self):
        return {
            "total_actions": len(self.model["action_history"]),
            "unique_actions": len(self.model["action_scores"]),
            "best_action": self.recommend(top_n=1)[0] if self.model["action_scores"] else None
        }


if __name__ == "__main__":
    # Teste rápido
    classifier = MLClassifier()
    classifier.train("Criar um site de vendas online", "desenvolvimento")
    classifier.train("Integrar API do PayPal", "financeiro")
    classifier.train("Otimizar código Python", "programacao")
    
    result = classifier.classify("Fazer integração com Stripe")
    print(f"Classificação: {result}")
    
    recommender = MLRecommender()
    recommender.record_action("criar modulo", {"tipo": "api"}, 0.8)
    recommender.record_action("otimizar codigo", {"tipo": "performance"}, 0.6)
    print(f"Recomendações: {recommender.recommend()}")
