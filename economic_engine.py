# -*- coding: utf-8 -*-
"""economic_engine.py - Motor de Economia para minimizar gastos com DeepSeek"""

import json
import os
import time
import hashlib
from datetime import datetime
from pathlib import Path


class EconomicEngine:
    """Motor de economia - cache, budget, prioridades."""
    
    def __init__(self, cache_dir='cache/economy', budget_per_day=50000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / 'response_cache.json'
        self.stats_file = self.cache_dir / 'usage_stats.json'
        self.budget_per_day = budget_per_day
        self.cache = self._load_cache()
        self.stats = self._load_stats()
        
    def _load_cache(self):
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def _load_stats(self):
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'total_tokens': 0, 'calls': 0, 'cache_hits': 0, 'daily': {}}
        
    def _save(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2)
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)
            
    def _make_key(self, prompt, model='deepseek'):
        raw = f'{model}:{prompt}'.encode('utf-8')
        return hashlib.md5(raw).hexdigest()
        
    def get_cached(self, prompt, model='deepseek', max_age_hours=24):
        key = self._make_key(prompt, model)
        if key in self.cache:
            entry = self.cache[key]
            age = time.time() - entry['timestamp']
            if age < max_age_hours * 3600:
                self.stats['cache_hits'] += 1
                self._save()
                return entry['response']
        return None
        
    def set_cached(self, prompt, response, model='deepseek'):
        key = self._make_key(prompt, model)
        self.cache[key] = {
            'response': response,
            'timestamp': time.time(),
            'model': model
        }
        self._save()
        
    def can_call_api(self, tokens_estimate=1000):
        today = datetime.now().strftime('%Y-%m-%d')
        daily = self.stats['daily'].get(today, 0)
        return daily + tokens_estimate <= self.budget_per_day
        
    def register_call(self, tokens_used):
        today = datetime.now().strftime('%Y-%m-%d')
        self.stats['total_tokens'] += tokens_used
        self.stats['calls'] += 1
        self.stats['daily'][today] = self.stats['daily'].get(today, 0) + tokens_used
        self._save()
        
    def get_stats(self):
        today = datetime.now().strftime('%Y-%m-%d')
        daily = self.stats['daily'].get(today, 0)
        return {
            'calls': self.stats['calls'],
            'tokens': self.stats['total_tokens'],
            'cache_hits': self.stats['cache_hits'],
            'daily_tokens': daily,
            'budget': self.budget_per_day,
            'remaining': self.budget_per_day - daily,
            'cache_size': len(self.cache)
        }


if __name__ == '__main__':
    e = EconomicEngine()
    print('EconomicEngine OK')
    print(json.dumps(e.get_stats(), indent=2))
