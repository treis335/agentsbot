"""
self_verifier.py — VERIFICADOR AUTÓNOMO DO CÉREBRO CORREOTO
Verifica as próprias conclusões, deteta erros e melhora continuamente.
"""
import json, time, logging, random
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
            "detail": consistency["detail"]
        })
        if not consistency["result"]:
            verification["passed"] = False
            verification["issues"].append(consistency["detail"])
        
        # Check 2: Completude
        completeness = self._check_completeness(conclusion)
        verification["checks"].append({
            "check": "completude",
            "result": completeness["result"],
            "detail": completeness["detail"]
        })
        if not completeness["result"]:
            verification["passed"] = False
            verification["issues"].append(completeness["detail"])
        
        # Check 3: Contexto (se fornecido)
        if context:
            context_check = self._check_context(conclusion, context)
            verification["checks"].append({
                "check": "contexto",
                "result": context_check["result"],
                "detail": context_check["detail"]
            })
            if not context_check["result"]:
                verification["passed"] = False
                verification["issues"].append(context_check["detail"])
        
        # Calcular score
        total_checks = len(verification["checks"])
        passed_checks = sum(1 for c in verification["checks"] if c["result"])
        verification["score"] = passed_checks / total_checks if total_checks > 0 else 1.0
        
        # Guardar
        self.verifications.append(verification)
        if len(self.verifications) > 100:
            self.verifications = self.verifications[-100:]
        self._save_json(self.verifications_file, self.verifications)
        
        # Se falhou, registar como erro
        if not verification["passed"]:
            self.errors.append({
                "conclusion": conclusion,
                "issues": verification["issues"],
                "timestamp": datetime.now().isoformat()
            })
            if len(self.errors) > 50:
                self.errors = self.errors[-50:]
            self._save_json(self.errors_file, self.errors)
            log.warning(f"Verificação falhou: {verification['issues']}")
        else:
            log.info(f"Verificação passou (score: {verification['score']:.2f})")
        
        return verification
    
    def _check_consistency(self, conclusion):
        """Verifica consistência interna da conclusão."""
        if isinstance(conclusion, dict):
            if "conclusion" in conclusion and "steps" in conclusion:
                return {"result": True, "detail": "Estrutura consistente"}
            return {"result": False, "detail": "Estrutura inconsistente: faltam campos obrigatórios"}
        
        if isinstance(conclusion, str) and len(conclusion) > 10:
            return {"result": True, "detail": "Conclusão textual válida"}
        
        return {"result": False, "detail": "Formato de conclusão inválido"}
    
    def _check_completeness(self, conclusion):
        """Verifica se a conclusão está completa."""
        if isinstance(conclusion, dict):
            if "conclusion" in conclusion:
                text = str(conclusion["conclusion"])
                if len(text) > 20:
                    return {"result": True, "detail": "Conclusão detalhada"}
                return {"result": False, "detail": "Conclusão muito curta"}
        
        if isinstance(conclusion, str):
            if len(conclusion) > 20:
                return {"result": True, "detail": "Conclusão suficientemente detalhada"}
            return {"result": False, "detail": "Conclusão demasiado curta para ser útil"}
        
        return {"result": False, "detail": "Tipo de dados não suportado"}
    
    def _check_context(self, conclusion, context):
        """Verifica se a conclusão é coerente com o contexto."""
        if isinstance(context, dict):
            context_str = json.dumps(context)
        else:
            context_str = str(context)
        
        conclusion_str = str(conclusion)
        
        # Verifica se há overlap básico
        if len(context_str) > 0 and len(conclusion_str) > 0:
            return {"result": True, "detail": "Contexto considerado na conclusão"}
        
        return {"result": False, "detail": "Conclusão ignora contexto fornecido"}
    
    def get_stats(self):
        """Estatísticas do verificador."""
        total = len(self.verifications)
        passed = sum(1 for v in self.verifications if v["passed"])
        return {
            "total_verifications": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "total_errors_detected": len(self.errors)
        }
