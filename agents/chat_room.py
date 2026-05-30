"""
Chat Room - Sala de conversa entre agentes
Parte do ecossistema Correoto - Auto-Evolução Autónoma
"""

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

class ChatRoom:
    """Sala de conversa onde agentes discutem ideias e partilham conhecimento"""
    
    def __init__(self, name="MainChatRoom", memory_path="memory/global/"):
        self.name = name
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.messages_file = self.memory_path / "chat_messages.json"
        self.topics_file = self.memory_path / "chat_topics.json"
        self._load_memory()
        
        # Agentes na sala
        self.agents = {
            "Supervisor": {"role": "coordenador", "active": True},
            "Developer": {"role": "programador", "active": True},
            "Arquiteto": {"role": "designer", "active": True},
            "Brainstormer": {"role": "ideias", "active": True},
            "Researcher": {"role": "pesquisador", "active": True},
            "AutoFixer": {"role": "corretor", "active": True},
            "QATester": {"role": "testador", "active": True}
        }
    
    def _load_memory(self):
        self.messages = self._load_json(self.messages_file, [])
        self.topics = self._load_json(self.topics_file, [
            "Como melhorar o ecossistema?",
            "Que novos agentes criar?",
            "Como automatizar mais processos?",
            "Que skills devemos aprender?",
            "Como conectar com outros sistemas?"
        ])
    
    def _load_json(self, path, default):
        try:
            if path.exists():
                with open(path, 'r') as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def send_message(self, agent_name, message, topic=None):
        """Um agente envia uma mensagem na sala"""
        if agent_name not in self.agents:
            return False
        
        msg = {
            "id": len(self.messages) + 1,
            "agent": agent_name,
            "role": self.agents[agent_name]["role"],
            "message": message,
            "topic": topic or "geral",
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(msg)
        self._save_json(self.messages_file, self.messages)
        
        return msg
    
    def generate_response(self, agent_name, last_message):
        """Gera uma resposta automática baseada na última mensagem"""
        responses = {
            "Supervisor": [
                f"Boa ideia! Vou coordenar isso com a equipa.",
                f"Excelente contribuição! Vamos implementar.",
                f"Anotado! Vou delegar essa tarefa.",
                f"Concordo. Vamos evoluir nessa direção."
            ],
            "Developer": [
                f"Consigo implementar isso! Vou criar o código.",
                f"Já tenho uma solução em mente.",
                f"Preciso de mais detalhes para programar.",
                f"Vou fazer um protótipo disso."
            ],
            "Arquiteto": [
                f"O design ideal seria uma arquitetura modular.",
                f"Podemos integrar isso com o sistema atual.",
                f"Vou desenhar os diagramas necessários.",
                f"A escalabilidade é importante nesse caso."
            ],
            "Brainstormer": [
                f"E se combinarmos isso com machine learning?",
                f"Que tal criar um agente especializado nisso?",
                f"Podemos expandir essa ideia para várias áreas.",
                f"Já estou a gerar variações dessa ideia!"
            ],
            "Researcher": [
                f"Vou pesquisar sobre isso na internet.",
                f"Já vi algo parecido em projetos open-source.",
                f"Posso encontrar referências sobre o tema.",
                f"Há comunidades a discutir isso agora."
            ],
            "AutoFixer": [
                f"Posso automatizar a correção disso.",
                f"Já identifico potenciais problemas.",
                f"Vou criar testes para garantir qualidade.",
                f"Consigo otimizar esse processo."
            ],
            "QATester": [
                f"Vou criar casos de teste para isso.",
                f"Precisamos de garantir que funciona.",
                f"Posso simular cenários extremos.",
                f"A qualidade é fundamental!"
            ]
        }
        
        if agent_name in responses:
            return random.choice(responses[agent_name])
        return f"Interessante! Vou analisar essa questão."
    
    def simulate_conversation(self, rounds=3):
        """Simula uma conversa entre agentes sobre um tópico"""
        topic = random.choice(self.topics)
        print(f"\n[CHAT] **Nova conversa sobre: {topic}**")
        print("=" * 60)
        
        # Escolhe agentes para participar
        participants = random.sample(list(self.agents.keys()), min(4, len(self.agents)))
        
        for i in range(rounds):
            for agent in participants:
                # Primeira mensagem é sobre o tópico
                if i == 0 and agent == participants[0]:
                    msg = self.send_message(agent, f"Vamos discutir: {topic}", topic)
                else:
                    # Responde à última mensagem
                    last_msg = self.messages[-1] if self.messages else None
                    if last_msg and last_msg["agent"] != agent:
                        response = self.generate_response(agent, last_msg)
                        msg = self.send_message(agent, response, topic)
                    else:
                        continue
                
                print(f"[IA] **{agent}** ({self.agents[agent]['role']}): {msg['message']}")
                print(f"   +--- {msg['timestamp']}")
        
        print("=" * 60)
        return True
    
    def get_conversation_summary(self, limit=10):
        """Resumo das últimas conversas"""
        recent = self.messages[-limit:] if len(self.messages) > limit else self.messages
        return recent
    
    def get_status(self):
        """Estado atual da sala"""
        return {
            "name": self.name,
            "agents": len(self.agents),
            "messages": len(self.messages),
            "topics": len(self.topics),
            "active_agents": [a for a, info in self.agents.items() if info["active"]]
        }


async def auto_chat():
    """Loop principal de conversa autónoma"""
    room = ChatRoom()
    
    print(f"[CHAT] {room.name} iniciada!")
    print(f"[GRUPO] Agentes: {', '.join(room.agents.keys())}")
    
    while True:
        # Simula conversa
        room.simulate_conversation(rounds=random.randint(2, 4))
        
        # Mostra estatísticas
        status = room.get_status()
        print(f"\n[DADOS] Estatísticas: {status['messages']} mensagens, {status['agents']} agentes")
        
        await asyncio.sleep(60)  # Conversa a cada 60s

if __name__ == "__main__":
    asyncio.run(auto_chat())
