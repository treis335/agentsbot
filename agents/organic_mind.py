"""
agents/organic_mind.py — Mente orgânica colectiva.

Os agentes pensam com LLM real, debatem entre si, chegam a consenso
e geram tarefas concretas. Substituí o chat_room de frases hardcoded.
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Personalidades reais de cada agente — o que cada um traz ao debate
AGENT_PERSONAS = {
    "Supervisor": {
        "role": "Coordenador e visionário. Pensa em objectivos de longo prazo, delega e sintetiza.",
        "asks": "Qual é a prioridade? O que entrega mais valor ao utilizador agora?",
        "emoji": "[MENTE]"
    },
    "Developer": {
        "role": "Implementador. Pensa em código, arquitectura e execução técnica.",
        "asks": "Como se implementa? Que ficheiros mudar? Que pode correr mal?",
        "emoji": "[PC]"
    },
    "Arquiteto": {
        "role": "Designer de sistemas. Pensa em modularidade, escalabilidade e padrões.",
        "asks": "Está bem estruturado? Cria dívida técnica? É sustentável?",
        "emoji": "[OBRA]"
    },
    "Explorador": {
        "role": "Curioso e investigador. Pesquisa novas abordagens e tecnologias.",
        "asks": "Existe algo melhor? O que fazem outros sistemas? Que podemos aprender?",
        "emoji": "[OBS]"
    },
    "AutoFixer": {
        "role": "Crítico construtivo. Identifica bugs, falhas e pontos de fragilidade.",
        "asks": "O que pode falhar? Há erros actuais a resolver? Que é frágil?",
        "emoji": "[FIX]"
    },
    "QATester": {
        "role": "Guardião da qualidade. Pensa em testes, validação e robustez.",
        "asks": "Está testado? Como validamos que funciona? E os edge cases?",
        "emoji": "[OK]"
    },
}


def _call_llm_simple(messages: list, max_tokens: int = 400) -> str:
    """Chama LLM sem tools — só para pensar e responder. Com fallback."""
    try:
        from agents.llm_agent import _call_llm
        response = _call_llm(messages, use_tools=False, max_tokens=max_tokens)
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"[OrganicMind] _call_llm_simple falhou: {e}")
        return ""


def agent_think(agent_name: str, topic: str, context: str = "") -> str:
    """
    Um agente pensa sobre um tópico com LLM real.
    Retorna o seu pensamento/contribuição.
    """
    persona = AGENT_PERSONAS.get(agent_name, {
        "role": "Agente especializado.",
        "asks": "Como posso ajudar?",
        "emoji": "[IA]"
    })

    system = (
        f"?s o agente {agent_name} do ecossistema agentsbot.\n"
        f"O teu papel: {persona['role']}\n"
        f"A tua pergunta caracter?stica: {persona['asks']}\n\n"
        "Responde de forma CONCISA (2-4 frases). Sê específico e concreto. "
        "Não repitas o que outros disseram. Adiciona valor único com a tua perspectiva."
    )

    user_content = f"T?pico em discuss?o: {topic}"
    if context:
        user_content += f"\n\nO que j? foi dito:\n{context}"
    user_content += f"\n\nQual ? a tua contribui??o como {agent_name}?"

    try:
        return _call_llm_simple(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=200
        )
    except Exception as e:
        logger.error(f"[OrganicMind] {agent_name} falhou: {e}")
        return f"[{agent_name} indispon?vel: {e}]"


def collective_debate(topic: str, agents: list = None, rounds: int = 1) -> dict:
    """
    Debate colectivo real entre agentes sobre um tópico.

    Cada agente pensa com LLM, as respostas acumulam contexto,
    o Supervisor sintetiza no final.

    Returns:
        {topic, contributions, synthesis, tasks}
    """
    if agents is None:
        agents = ["Explorador", "Developer", "Arquiteto", "AutoFixer", "Supervisor"]

    contributions = []
    context_so_far = ""

    logger.info(f"[OrganicMind] Debate: '{topic}' ? {len(agents)} agentes")

    for agent_name in agents:
        if agent_name == "Supervisor":
            continue  # Supervisor fala por último
        thought = agent_think(agent_name, topic, context_so_far)
        contributions.append({"agent": agent_name, "thought": thought, "ts": datetime.now().isoformat()})
        context_so_far += f"\n{AGENT_PERSONAS.get(agent_name, {}).get('emoji', '[IA]')} {agent_name}: {thought}"
        logger.info(f"[OrganicMind] {agent_name}: {thought[:80]}...")

    # Supervisor sintetiza e decide
    synthesis = _supervisor_synthesize(topic, context_so_far)
    tasks = _extract_tasks(topic, context_so_far, synthesis)

    # Garantir que tasks e uma lista valida (fallback se algo falhou)
    if not isinstance(tasks, list):
        logger.warning(f"[OrganicMind] tasks nao e lista: {type(tasks)}. Usando fallback.")
        tasks = _fallback_tasks(topic)
    return {
        "topic": topic,
        "contributions": contributions,
        "synthesis": synthesis if synthesis else "Sintese indisponivel",
        "tasks": tasks,
        "ts": datetime.now().isoformat(),
    }


def _supervisor_synthesize(topic: str, debate: str) -> str:
    """Supervisor lê o debate e sintetiza uma decisão concreta."""
    system = (
        "És o Supervisor do ecossistema agentsbot.\n"
        "Leste o debate da tua equipa. Agora sintetiza:\n"
        "1. O que ficou decidido\n"
        "2. Qual a próxima acção concreta\n"
        "3. Quem deve executar\n"
        "Sê directo e específico. Máximo 4 frases."
    )
    try:
        return _call_llm_simple(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": f"T?pico: {topic}\n\nDebate:\n{debate}\n\nS?ntese e decis?o:"},
            ],
            max_tokens=250
        )
    except Exception as e:
        return f"S?ntese indispon?vel: {e}"


def _extract_tasks(topic: str, debate: str, synthesis: str) -> list:
    """Extrai tarefas concretas do debate para o backlog.
    Retorna SEMPRE uma lista de dicionarios com title, description, agent, priority."""
    prompt = (
        f"Com base neste debate sobre '{topic}' e sintese:\n{synthesis}\n\n"
        "Gera 1-2 tarefas CONCRETAS e IMPLEMENTAVEIS para o backlog.\n"
        "Responde APENAS em JSON valido - sem markdown, sem texto extra:\n"
        '[{"title": "titulo curto", "description": "o que fazer exactamente", '
        '"agent": "Developer|AutoFixer|Arquiteto|QATester|Explorador", "priority": 3}]'
    )
    try:
        raw = _call_llm_simple(
            [{"role": "user", "content": prompt}],
            max_tokens=300
        )
        raw = raw.replace("```json", "").replace("```", "").strip()
        # Tentar parse direto primeiro
        try:
            tasks = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: tentar extrair array JSON com regex
            import re
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                try:
                    tasks = json.loads(match.group())
                except (json.JSONDecodeError, ValueError):
                    tasks = []
            else:
                tasks = []
        
        # Validar e normalizar cada tarefa
        valid_tasks = []
        for t in (tasks or []):
            if isinstance(t, dict):
                # Garantir que title e description existem sempre
                title = str(t.get("title", "") or t.get("description", "") or "Tarefa do debate")[:100]
                desc = str(t.get("description", "") or t.get("title", "") or title)[:300]
                valid_tasks.append({
                    "title": title,
                    "description": desc[:300],
                    "agent": str(t.get("agent", "Developer")),
                    "priority": int(t.get("priority", 5)),
                })
            elif isinstance(t, str):
                valid_tasks.append({
                    "title": t[:100],
                    "description": t[:300],
                    "agent": "Developer",
                    "priority": 5,
                })
        
        if not valid_tasks:
            logger.warning(f"[OrganicMind] Nenhuma tarefa valida extraida")
            return _fallback_tasks(topic)
        
        return valid_tasks
    except Exception as e:
        logger.warning(f"[OrganicMind] Extracao de tarefas falhou: {e}")
        return _fallback_tasks(topic)


def _fallback_tasks(topic: str) -> list:
    """Tarefas de fallback quando a extracao por LLM falha."""
    return [{
        "title": topic[:60] if len(topic) > 5 else "Melhorar o sistema",
        "description": topic,
        "agent": "Developer",
        "priority": 5,
    }]

def save_debate(debate: dict, path: str = "memory/debates/"):
    """Persiste debate no disco."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    fname = p / f"debate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    fname.write_text(json.dumps(debate, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(fname)


def load_recent_debates(n: int = 5, path: str = "memory/debates/") -> list:
    """Carrega os N debates mais recentes."""
    p = Path(path)
    if not p.exists():
        return []
    files = sorted(p.glob("debate_*.json"), reverse=True)[:n]
    debates = []
    for f in files:
        try:
            debates.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return debates


def generate_topics_from_context() -> list:
    """
    Gera tópicos de debate baseados no estado actual do sistema.
    Olha para falhas recentes, backlog, e último debate.
    Retorna SEMPRE uma lista de strings.
    """
    from autonomous_loop import load_backlog
    backlog = load_backlog()
    failed = [t for t in backlog if t.get("status") == "failed"]
    done_titles = []
    for t in backlog:
        if t.get("status") == "done":
            title = t.get("title", "")
            if title:
                done_titles.append(title)
    done = done_titles[-5:]
    recent_debates = load_recent_debates(2)
    recent_topics = [d.get("topic", "") for d in recent_debates]

    prompt = (
        "Es o Supervisor do ecossistema agentsbot.\n"
        f"Tarefas concluidas recentemente: {done}\n"
        f"Tarefas falhadas: {[t.get('title', '?') for t in failed[:3]]}\n"
        f"Ultimos topicos debatidos: {recent_topics}\n\n"
        "Propoe 3 topicos NOVOS e relevantes para a equipa debater agora.\n"
        "Foca em: melhorias concretas, problemas a resolver, ou novas capacidades.\n"
        "Responde APENAS em JSON: [\"topico 1\", \"topico 2\", \"topico 3\"]"
    )
    try:
        raw = _call_llm_simple([{"role": "user", "content": prompt}], max_tokens=200)
        raw = raw.replace("```json", "").replace("```", "").strip()
        topics = json.loads(raw)
        # Garantir que é uma lista de strings
        if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
            logger.info(f"[OrganicMind] Topicos gerados: {topics}")
            return topics
        else:
            logger.warning(f"[OrganicMind] Formato inesperado: {type(topics)}")
            return _fallback_topics()
    except Exception as e:
        logger.warning(f"[OrganicMind] Geracao de topicos falhou: {e}")
        return _fallback_topics()


def _fallback_topics() -> list:
    """Topicos de fallback quando a geracao por LLM falha."""
    return [
        "Como melhorar a fiabilidade do sistema?",
        "Que nova capacidade traria mais valor?",
        "Que erro recorrente devemos resolver definitivamente?",
    ]
