"""
self_verifier.py — VERIFICADOR AUTÓNOMO DO CÉREBRO CORREOTO
Verifica as próprias conclusões, deteta erros e melhora continuamente.
"""
import os, json, time, logging, random
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE / "memory" / "global"
os.makedirs(MEMORY_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VERIFIER] %(message)s")
log = logging.getLogger("self_verifier")

class SelfVerifier:
    """Verificador automático que valida conclusões e deteta erros."""
    
    def __init__(self):
        self.verifications_file = MEMORY_DIR / "verifications.json"
        self.errors_file = MEMORY_DIR / "self_detected_errors.json"
        self.verifications = self._load_json(self.verifications_file, [])
        self.errors = self._load_json(self.errors_file, [])
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
    
    def verify(self, conclusion, context=None):
        """Verifica uma conclusão e devolve validação."""
        self.cycle += 1
        log.info(f"Ciclo {self.cycle}: Verificando conclusão...")
        
        verification = {
            "conclusion": conclusion,
            "checks": [],
            "passed": True,
            "score": 1.0,
            "issues": [],
            "timestamp": datetime.now().isoformat(),
            "cycle": self.cycle
        }
        
        # Check 1: Consistência interna
        consistency = self._check_consistency(conclusion)
        verification["checks"].append({
            "check": "consistência_interna",
            "result": consistency["result"],
            "score": consistency["score"]
        })
        if not consistency["result"]:
            verification["passed"] = False
            verification["issues"].append(consistency["reason"])
        
        # Check 2: Completude
        completeness = self._check_completeness(conclusion)
        verification["checks"].append({
            "check": "completude",
            "result": completeness["result"],
            "score": completeness["score"]
        })
        if not completeness["result"]:
            verification["passed"] = False
            verification["issues"].append(completeness["reason"])
        
        # Check 3: Lógica
        logic = self._check_logic(conclusion)
        verification["checks"].append({
            "check": "lógica",
            "result": logic["result"],
            "score": logic["score"]
        })
        if not logic["result"]:
            verification["passed"] = False
            verification["issues"].append(logic["reason"])
        
        # Score final
        scores = [c["score"] for c in verification["checks"]]
        verification["score"] = sum(scores) / len(scores) if scores else 1.0
        
        self.verifications.append(verification)
        self._save_json(self.verifications_file, self.verifications)
        
        return verification
    
    def _check_consistency(self, text):
        """Verifica se o texto é consistente."""
        if not text or len(text) < 10:
            return {"result": False, "score": 0.3, "reason": "Texto muito curto ou vazio"}
        
        # Verificar contradições
        contradictions = ["mas por outro lado não", "no entanto é falso", "contradiz"]
        for c in contradictions:
            if c in text.lower():
                return {"result": False, "score": 0.5, "reason": f"Possível contradição: '{c}'"}
        
        return {"result": True, "score": 1.0, "reason": ""}
    
    def _check_completeness(self, text):
        """Verifica se o texto está completo."""
        required_markers = [":", ".", "\n"]
        for marker in required_markers:
            if marker not in text:
                return {"result": False, "score": 0.5, "reason": f"Falta marcador: '{marker}'"}
        
        return {"result": True, "score": 1.0, "reason": ""}
    
    def _check_logic(self, text):
        """Verifica a lógica do texto."""
        logical_words = ["porque", "portanto", "logo", "então", "se", "então"]
        has_logic = any(word in text.lower() for word in logical_words)
        
        if not has_logic:
            return {"result": False, "score": 0.6, "reason": "Falta estrutura lógica (porque, portanto, etc)"}
        
        return {"result": True, "score": 1.0, "reason": ""}
    
    def detect_error(self, error_type, context, severity="medium"):
        """Regista um erro detetado automaticamente."""
        error = {
            "type": error_type,
            "context": context,
            "severity": severity,
            "detected_at": datetime.now().isoformat(),
            "cycle": self.cycle,
            "fixed": False
        }
        self.errors.append(error)
        self._save_json(self.errors_file, self.errors)
        log.warning(f"Erro detetado: {error_type} - {context}")
        return error
    
    def get_stats(self):
        """Estatísticas do verificador."""
        return {
            "total_verifications": len(self.verifications),
            "total_errors": len(self.errors),
            "avg_score": sum(v["score"] for v in self.verifications) / len(self.verifications) if self.verifications else 0,
            "cycles": self.cycle
        }

# Singleton
_verifier_instance = None

def get_verifier():
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = SelfVerifier()
    return _verifier_instance
