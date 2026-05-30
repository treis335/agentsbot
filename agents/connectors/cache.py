"""
agents/connectors/cache.py — Reasoning Cache Layer

Cache inteligente para respostas do LLM.
Evita recomputar respostas idênticas ou similares.
Inspirado no Reasonix (cache-first agent).
"""
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Any

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

class ReasoningCache:
    """Cache de reasoning para evitar recomputar respostas."""
    
    def __init__(self, ttl_hours: int = 24, max_entries: int = 1000):
        self.ttl = timedelta(hours=ttl_hours)
        self.max_entries = max_entries
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.cache_file = os.path.join(CACHE_DIR, "reasoning_cache.json")
        self._load()
    
    def _load(self):
        """Carrega cache do disco."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cache = {}
        else:
            self._cache = {}
    
    def _save(self):
        """Salva cache no disco."""
        # Limpar entradas expiradas
        now = datetime.now()
        self._cache = {
            k: v for k, v in self._cache.items()
            if datetime.fromisoformat(v["cached_at"]) + self.ttl > now
        }
        # Limitar tamanho
        if len(self._cache) > self.max_entries:
            sorted_keys = sorted(self._cache.keys(), 
                                key=lambda k: self._cache[k]["cached_at"])
            for k in sorted_keys[:len(self._cache) - self.max_entries]:
                del self._cache[k]
        
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)
    
    def _make_key(self, prompt: str, model: str, system_prompt: str = "") -> str:
        """Cria chave única para um par prompt+model."""
        raw = f"{model}||{system_prompt}||{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def get(self, prompt: str, model: str, system_prompt: str = "") -> Optional[str]:
        """Obtém resposta em cache se existir e válida."""
        key = self._make_key(prompt, model, system_prompt)
        if key in self._cache:
            entry = self._cache[key]
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if datetime.now() - cached_at < self.ttl:
                entry["hits"] = entry.get("hits", 0) + 1
                self._save()
                return entry["response"]
        return None
    
    def set(self, prompt: str, response: str, model: str, system_prompt: str = ""):
        """Guarda resposta em cache."""
        key = self._make_key(prompt, model, system_prompt)
        self._cache[key] = {
            "response": response,
            "model": model,
            "cached_at": datetime.now().isoformat(),
            "hits": 0,
            "prompt_preview": prompt[:100]
        }
        self._save()
    
    def stats(self) -> dict:
        """Estatísticas do cache."""
        total = len(self._cache)
        total_hits = sum(v.get("hits", 0) for v in self._cache.values())
        return {
            "total_entries": total,
            "total_hits": total_hits,
            "hit_rate": round(total_hits / max(total, 1), 2),
            "oldest": min((v["cached_at"] for v in self._cache.values()), default="N/A"),
            "newest": max((v["cached_at"] for v in self._cache.values()), default="N/A")
        }
    
    def clear(self):
        """Limpa todo o cache."""
        self._cache = {}
        self._save()


# Instância global
_cache = None

def get_cache() -> ReasoningCache:
    global _cache
    if _cache is None:
        _cache = ReasoningCache()
    return _cache
