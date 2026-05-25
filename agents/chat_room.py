"""
Sala de Conversa entre Agentes
Permite discussões, partilha de ideias e colaboração entre múltiplos agentes
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class ChatRoom:
    def __init__(self, name: str, topic: str):
        self.name = name
        self.topic = topic
        self.messages: List[Dict] = []
        self.participants: List[str] = []
        self.log_path = Path(f"memory/chats/{name}.json")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def add_participant(self, agent_name: str):
        if agent_name not in self.participants:
            self.participants.append(agent_name)
            self._log(f"Sistema", f"{agent_name} entrou na sala")
    
    def send_message(self, agent_name: str, message: str):
        msg = {
            "agent": agent_name,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(msg)
        self._save()
        return msg
    
    def _log(self, agent: str, message: str):
        self.send_message(agent, message)
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        return self.messages[-limit:]
    
    def _save(self):
        data = {
            "name": self.name,
            "topic": self.topic,
            "participants": self.participants,
            "messages": self.messages[-100:]  # Keep last 100
        }
        self.log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


class ChatManager:
    """Gerencia múltiplas salas de conversa"""
    
    def __init__(self):
        self.rooms: Dict[str, ChatRoom] = {}
        self._load_rooms()
    
    def create_room(self, name: str, topic: str) -> ChatRoom:
        if name not in self.rooms:
            self.rooms[name] = ChatRoom(name, topic)
        return self.rooms[name]
    
    def get_or_create_room(self, name: str, topic: str = "") -> ChatRoom:
        if name not in self.rooms:
            self.rooms[name] = ChatRoom(name, topic)
        return self.rooms[name]
    
    def _load_rooms(self):
        rooms_dir = Path("memory/chats")
        if rooms_dir.exists():
            for f in rooms_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    room = ChatRoom(data["name"], data["topic"])
                    room.messages = data["messages"]
                    room.participants = data["participants"]
                    self.rooms[data["name"]] = room
                except:
                    pass
    
    def list_rooms(self) -> List[str]:
        return list(self.rooms.keys())
    
    def get_room(self, name: str) -> Optional[ChatRoom]:
        return self.rooms.get(name)
