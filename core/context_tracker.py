"""
core/context_tracker.py - Rastreador de Contexto
Impede que o Supervisor confunda topicos de conversa diferentes.
"""

import json
import os
from datetime import datetime

MEMORY_DIR = "memory"
CONTEXT_FILE = os.path.join(MEMORY_DIR, "context.json")

class ContextTracker:
    """
    Rastreador de contexto de conversa.
    Mantem um historico de topicos e impede confusao entre eles.
    """
    
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.contexts = self._load()
    
    def _load(self):
        if os.path.exists(CONTEXT_FILE):
            try:
                with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "current_context": "default",
            "contexts": {
                "default": {
                    "topic": "Conversa geral",
                    "last_interaction": None,
                    "interaction_count": 0,
                    "history": []
                }
            }
        }
    
    def _save(self):
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.contexts, f, indent=2, ensure_ascii=False)
    
    def detect_context(self, message):
        """
        Detecta o contexto de uma mensagem baseado em palavras-chave.
        Devolve o nome do contexto.
        """
        msg_lower = message.lower()
        
        # Palavras-chave para cada contexto
        keywords = {
            "dashboard": ["dashboard", "visual", "interface", "grafico", "graficos", "metricas"],
            "memoria": ["memoria", "memory", "lembrar", "esquecer", "historico"],
            "git": ["git", "github", "push", "commit", "repo", "repositorio"],
            "agentes": ["agente", "agentes", "equipa", "team", "criar agente"],
            "reboot": ["reboot", "reiniciar", "reset", "restart"],
            "evolucao": ["evoluir", "evolucao", "melhorar", "upgrade", "cognitivo"],
            "bugs": ["bug", "erro", "problema", "falha", "crash"],
            "telegram": ["telegram", "notificacao", "alerta"],
        }
        
        # Verificar correspondencias
        scores = {}
        for ctx, words in keywords.items():
            score = sum(1 for word in words if word in msg_lower)
            if score > 0:
                scores[ctx] = score
        
        if scores:
            best_context = max(scores, key=scores.get)
            return best_context
        
        return "default"
    
    def switch_context(self, context_name, topic=None):
        """Muda para um contexto especifico."""
        if context_name not in self.contexts["contexts"]:
            self.contexts["contexts"][context_name] = {
                "topic": topic or f"Contexto: {context_name}",
                "last_interaction": None,
                "interaction_count": 0,
                "history": []
            }
        
        self.contexts["current_context"] = context_name
        self._save()
        return context_name
    
    def add_interaction(self, role, content, context_name=None):
        """Regista uma interacao no contexto atual."""
        ctx = context_name or self.contexts["current_context"]
        
        if ctx not in self.contexts["contexts"]:
            self.switch_context(ctx)
        
        entry = {
            "role": role,
            "content": content[:200],
            "timestamp": datetime.now().isoformat()
        }
        
        self.contexts["contexts"][ctx]["history"].append(entry)
        self.contexts["contexts"][ctx]["last_interaction"] = datetime.now().isoformat()
        self.contexts["contexts"][ctx]["interaction_count"] += 1
        self.contexts["current_context"] = ctx
        
        # Manter apenas os ultimos 20 para nao crescer infinito
        if len(self.contexts["contexts"][ctx]["history"]) > 20:
            self.contexts["contexts"][ctx]["history"] = \
                self.contexts["contexts"][ctx]["history"][-20:]
        
        self._save()
    
    def get_current_context(self):
        """Devolve o contexto atual."""
        ctx_name = self.contexts["current_context"]
        ctx = self.contexts["contexts"].get(ctx_name, {})
        return {
            "name": ctx_name,
            "topic": ctx.get("topic", "Desconhecido"),
            "interactions": ctx.get("interaction_count", 0),
            "last_interaction": ctx.get("last_interaction")
        }
    
    def get_context_history(self, context_name=None):
        """Devolve o historial de um contexto."""
        ctx = context_name or self.contexts["current_context"]
        ctx_data = self.contexts["contexts"].get(ctx, {})
        return ctx_data.get("history", [])
    
    def get_all_contexts(self):
        """Devolve todos os contextos."""
        return {
            name: {
                "topic": data.get("topic"),
                "interactions": data.get("interaction_count", 0),
                "last_interaction": data.get("last_interaction")
            }
            for name, data in self.contexts["contexts"].items()
        }
    
    def format_context_for_prompt(self):
        """Formata o contexto atual para usar no prompt do LLM."""
        ctx = self.get_current_context()
        history = self.get_context_history()
        
        prompt = f"Contexto atual: {ctx['topic']}\n"
        prompt += f"Interacoes neste contexto: {ctx['interactions']}\n\n"
        
        if history:
            prompt += "Historico recente:\n"
            for entry in history[-5:]:
                prompt += f"[{entry['role']}] {entry['content'][:150]}\n"
        
        return prompt
