"""
Ecossistema Correoto - Sistema Central de Coordenação
Conecta agentes, salas, skills, dashboards e aprendizado contínuo
"""

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from agents.chat_room import ChatManager
from agents.skills_manager import SkillsManager

class Ecosystem:
    """Coração do ecossistema - coordena tudo"""
    
    def __init__(self):
        self.chat_manager = ChatManager()
        self.skills_manager = SkillsManager()
        self.agents_online: List[str] = []
        self.brainstorm_topics: List[str] = []
        self.innovation_log: List[Dict] = []
        self.memory_path = Path("memory/ecosystem.json")
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_memory()
        
        # Criar salas padrão
        self._setup_default_rooms()
    
    def _setup_default_rooms(self):
        """Cria salas de conversa padrão"""
        rooms = [
            ("brainstorm", "[IDEA] Brainstorming de ideias e inovação"),
            ("code-review", "[BUSCA] Revisão de código e melhoria contínua"),
            ("architecture", "[OBRA] Discussão de arquitetura e design"),
            ("skills", "[LIVRO] Aprendizagem e desenvolvimento de skills"),
            ("general", "[WEB] Discussões gerais do ecossistema"),
        ]
        for name, topic in rooms:
            self.chat_manager.create_room(name, topic)
    
    def register_agent(self, agent_name: str):
        """Regista um agente no ecossistema"""
        if agent_name not in self.agents_online:
            self.agents_online.append(agent_name)
            # Entrar nas salas principais
            for room_name in ["general", "brainstorm"]:
                room = self.chat_manager.get_room(room_name)
                if room:
                    room.add_participant(agent_name)
            self._log_innovation(f"[IA] Agente {agent_name} entrou no ecossistema")
            self._save_memory()
    
    def brainstorm(self, topic: str) -> str:
        """Gera uma ideia inovadora sobre um tópico"""
        ideas = [
            f"[IDEA] Criar um sistema de auto-aprendizagem baseado em {topic}",
            f"[FIX] Desenvolver uma ferramenta de {topic} com agentes colaborativos",
            f"[START] Implementar {topic} como servi?o no ecossistema",
            f"[DADOS] Dashboard interativo para monitorizar {topic} em tempo real",
            f"[MAO] Conectar {topic} com agentes externos para troca de conhecimento",
            f"[MENTE] Treinar agentes especializados em {topic}",
            f"[RAPIDO] Otimizar {topic} com machine learning",
            f"[MUNDO] Expandir {topic} para m?ltiplos idiomas e contextos",
        ]
        idea = random.choice(ideas)
        self._log_innovation(f"[IDEA] Brainstorm: {idea}")
        self.brainstorm_topics.append(topic)
        self._save_memory()
        return idea
    
    def discuss_in_room(self, room_name: str, agent_name: str, message: str):
        """Envia uma mensagem para uma sala de conversa"""
        room = self.chat_manager.get_room(room_name)
        if room:
            room.send_message(agent_name, message)
            return True
        return False
    
    def learn_new_skill(self) -> Optional[Dict]:
        """Tenta aprender uma nova skill"""
        skill = self.skills_manager.discover_new_skill()
        if skill:
            self._log_innovation(f"[LIVRO] Nova skill aprendida: {skill.name} (n?vel {skill.level})")
            self._save_memory()
            return {"name": skill.name, "category": skill.category, "level": skill.level}
        return None
    
    def get_ecosystem_status(self) -> Dict:
        """Retorna o estado completo do ecossistema"""
        return {
            "agents_online": len(self.agents_online),
            "agents_list": self.agents_online,
            "rooms": self.chat_manager.list_rooms(),
            "skills": self.skills_manager.get_stats(),
            "brainstorm_topics": self.brainstorm_topics[-10:],
            "innovations": self.innovation_log[-20:],
            "last_update": datetime.now().isoformat()
        }
    
    def _log_innovation(self, description: str):
        self.innovation_log.append({
            "timestamp": datetime.now().isoformat(),
            "description": description
        })
    
    def _save_memory(self):
        data = {
            "agents_online": self.agents_online,
            "brainstorm_topics": self.brainstorm_topics,
            "innovation_log": self.innovation_log[-100:],
            "last_save": datetime.now().isoformat()
        }
        self.memory_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    def _load_memory(self):
        if self.memory_path.exists():
            try:
                data = json.loads(self.memory_path.read_text())
                self.agents_online = data.get("agents_online", [])
                self.brainstorm_topics = data.get("brainstorm_topics", [])
                self.innovation_log = data.get("innovation_log", [])
            except:
                pass


class AutoEvolver:
    """Sistema que faz o ecossistema evoluir automaticamente"""
    
    def __init__(self, ecosystem: Ecosystem):
        self.ecosystem = ecosystem
        self.evolution_cycles = 0
    
    async def evolve(self) -> List[str]:
        """Executa um ciclo de evolução"""
        actions = []
        self.evolution_cycles += 1
        
        # 1. Tentar aprender nova skill
        skill = self.ecosystem.learn_new_skill()
        if skill:
            actions.append(f"[LIVRO] Aprendi {skill['name']} (n?vel {skill['level']})")
        
        # 2. Gerar brainstorm
        topics = ["IA", "automação", "dashboards", "agentes", "skills", "inovação"]
        topic = random.choice(topics)
        idea = self.ecosystem.brainstorm(topic)
        actions.append(f"[IDEA] {idea}")
        
        # 3. Discussão em sala
        rooms = self.ecosystem.chat_manager.list_rooms()
        if rooms:
            room = random.choice(rooms)
            agent = random.choice(self.ecosystem.agents_online) if self.ecosystem.agents_online else "Supervisor"
            msg = f"[CHAT] Discuss?o autom?tica: Como podemos melhorar {topic}?"
            self.ecosystem.discuss_in_room(room, agent, msg)
            actions.append(f"[CHAT] Discuss?o iniciada em {room}")
        
        # 4. Usar skills existentes
        skills = self.ecosystem.skills_manager.list_skills()
        if skills:
            skill = random.choice(skills)
            leveled_up = self.ecosystem.skills_manager.use_skill(skill.name)
            if leveled_up:
                actions.append(f"[UP] {skill.name} subiu para n?vel {skill.level}!")
        
        # 5. Registrar inovação
        self.ecosystem._log_innovation(f"[LOOP] Ciclo de evolu??o #{self.evolution_cycles} conclu?do")
        
        return actions
