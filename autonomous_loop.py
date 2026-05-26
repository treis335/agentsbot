"""
autonomous_loop.py
Motor de autonomia do ecossistema Correoto.
Corre para sempre — acorda, pensa, age, reporta, dorme, repete.
"""

import json
import os
import time
import random
import asyncio
from datetime import datetime
from pathlib import Path


# ─── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────

CYCLE_INTERVAL_MINUTES = 15        # Ciclo principal (acordar + trabalhar)
BRAINSTORM_INTERVAL_CYCLES = 4     # Brainstorm a cada N ciclos sem tarefas
MAX_TASKS_PER_CYCLE = 2            # Máximo de tarefas por ciclo
MEMORY_DIR = Path("memory")
BACKLOG_FILE = MEMORY_DIR / "backlog.json"
LOG_FILE = MEMORY_DIR / "autonomous_log.md"


# ─── AGENTES DA EQUIPA ─────────────────────────────────────────────────────────

AGENTS = {
    "supervisor":     "agents/souls/supervisor.md",
    "developer":      "agents/souls/developer.md",
    "arquiteto":      "agents/souls/arquiteto.md",
    "auto_fixer":     "agents/souls/auto_fixer.md",
    "auto_evolver":   "agents/souls/auto_evolver.md",
    "qa_tester":      "agents/souls/qa_tester.md",
    "gestor_memoria": "agents/souls/gestor_memoria.md",
}

# Papéis de cada agente no brainstorm
AGENT_ROLES = {
    "supervisor":     "Coordenação, prioridades e visão global",
    "developer":      "Implementação técnica e código",
    "arquiteto":      "Estrutura do sistema e design patterns",
    "auto_fixer":     "Bugs, erros e estabilidade",
    "auto_evolver":   "Melhorias, otimizações e novas features",
    "qa_tester":      "Qualidade, testes e validação",
    "gestor_memoria": "Memória, contexto e conhecimento acumulado",
}


# ─── BACKLOG DE TAREFAS ────────────────────────────────────────────────────────

def load_backlog() -> list:
    MEMORY_DIR.mkdir(exist_ok=True)
    if not BACKLOG_FILE.exists():
        return []
    with open(BACKLOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_backlog(backlog: list):
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(BACKLOG_FILE, "w", encoding="utf-8") as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)


def add_to_backlog(title: str, description: str, priority: int = 5,
                   source: str = "brainstorm"):
    """Adiciona tarefa ao backlog. Prioridade: 1 (alta) a 10 (baixa)."""
    backlog = load_backlog()
    task = {
        "id": f"task_{int(time.time())}_{random.randint(100, 999)}",
        "title": title,
        "description": description,
        "priority": priority,
        "source": source,
        "created": datetime.now().isoformat(),
        "status": "pending",
    }
    backlog.append(task)
    backlog.sort(key=lambda x: x["priority"])
    save_backlog(backlog)
    return task


def get_next_task() -> dict | None:
    """Retorna a próxima tarefa pendente de maior prioridade."""
    backlog = load_backlog()
    for task in backlog:
        if task["status"] == "pending":
            return task
    return None


def mark_task_done(task_id: str, result: str = ""):
    backlog = load_backlog()
    for task in backlog:
        if task["id"] == task_id:
            task["status"] = "done"
            task["completed"] = datetime.now().isoformat()
            task["result"] = result
    save_backlog(backlog)


def mark_task_failed(task_id: str, reason: str = ""):
    backlog = load_backlog()
    for task in backlog:
        if task["id"] == task_id:
            task["status"] = "failed"
            task["failed_at"] = datetime.now().isoformat()
            task["reason"] = reason
    save_backlog(backlog)


# ─── LOG DE AUTONOMIA ──────────────────────────────────────────────────────────

def log(message: str, level: str = "INFO"):
    MEMORY_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌",
             "BRAINSTORM": "💡", "SLEEP": "😴", "WAKE": "🌅"}.get(level, "•")
    entry = f"[{timestamp}] {emoji} {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
    print(entry.strip())


# ─── BRAINSTORM AUTÓNOMO ───────────────────────────────────────────────────────

# Ideias pré-carregadas para brainstorm autónomo
# (O sistema real chamaria a LLM — aqui é o template de integração)
BRAINSTORM_PROMPTS = [
    "Que melhorias podemos fazer ao sistema de logs?",
    "Como tornar o orchestrator mais eficiente?",
    "Que novas ferramentas poderiam ser úteis para os agentes?",
    "Como melhorar a comunicação entre agentes?",
    "Que testes de stress devemos implementar?",
    "Como otimizar o uso de tokens nas chamadas à LLM?",
    "Que sistema de alertas seria útil para o Joel?",
    "Como melhorar o sistema de memória persistente?",
    "Que métricas devemos monitorizar automaticamente?",
    "Como tornar o sistema mais resiliente a falhas?",
]

def autonomous_brainstorm(orchestrator=None) -> list:
    """
    Sessão de brainstorm autónomo entre agentes.
    Se orchestrator for fornecido, usa a LLM real.
    Caso contrário, usa ideias pré-definidas como fallback.
    """
    log("Sessão de brainstorm autónomo iniciada", "BRAINSTORM")
    ideas = []

    if orchestrator:
        # Integração real com LLM
        prompt = f"""
        És o Supervisor do ecossistema Correoto.
        A tua equipa está disponível: {', '.join(AGENTS.keys())}.
        
        Faz uma sessão de brainstorm rápida (máx 3 ideias concretas e implementáveis).
        Para cada ideia, indica:
        - Título (curto)
        - Descrição (o que fazer exatamente)
        - Prioridade (1-10, sendo 1 mais urgente)
        - Qual agente deve executar
        
        Responde apenas em JSON:
        [{{"title": "...", "description": "...", "priority": 5, "agent": "..."}}]
        """
        try:
            response = orchestrator.think(prompt)
            ideas = json.loads(response)
            log(f"Brainstorm gerou {len(ideas)} ideias via LLM", "BRAINSTORM")
        except Exception as e:
            log(f"Brainstorm LLM falhou ({e}), usando fallback", "ERROR")
            ideas = _brainstorm_fallback()
    else:
        ideas = _brainstorm_fallback()

    # Adicionar ideias ao backlog
    for idea in ideas:
        task = add_to_backlog(
            title=idea.get("title", "Ideia sem título"),
            description=idea.get("description", ""),
            priority=idea.get("priority", 5),
            source="brainstorm_autonomo",
        )
        log(f"Ideia adicionada ao backlog: '{task['title']}' (prioridade {task['priority']})",
            "BRAINSTORM")

    return ideas


def _brainstorm_fallback() -> list:
    """Fallback com ideias pré-definidas quando LLM não está disponível."""
    selected = random.sample(BRAINSTORM_PROMPTS, min(3, len(BRAINSTORM_PROMPTS)))
    return [
        {"title": idea, "description": idea, "priority": random.randint(3, 7)}
        for idea in selected
    ]


# ─── CICLO AUTÓNOMO PRINCIPAL ──────────────────────────────────────────────────

class AutonomousLoop:
    """
    Motor principal de autonomia.
    Corre indefinidamente — acorda, trabalha, reporta, dorme.
    """

    def __init__(self, orchestrator=None, telegram_bot=None):
        """
        Args:
            orchestrator:  Instância do orchestrator principal (para LLM)
            telegram_bot:  Bot do Telegram para enviar relatórios ao Joel
        """
        self.orchestrator = orchestrator
        self.telegram_bot = telegram_bot
        self.cycle_count = 0
        self.tasks_completed = 0
        self.is_running = False
        self.paused = False  # Joel pode pausar pelo Telegram

        MEMORY_DIR.mkdir(exist_ok=True)
        log("AutonomousLoop inicializado", "INFO")

    def start(self):
        """Inicia o loop autónomo. Bloqueia até ser interrompido."""
        self.is_running = True
        log("🚀 Loop autónomo INICIADO", "WAKE")
        self._notify_joel("🤖 Sistema Correoto online!\n"
                          f"Ciclo a cada {CYCLE_INTERVAL_MINUTES} min.\n"
                          "Vou trabalhar autonomamente e reportar aqui.")

        try:
            while self.is_running:
                if not self.paused:
                    self._run_cycle()
                else:
                    log("Sistema em pausa (comando do Joel)", "SLEEP")

                log(f"💤 A dormir {CYCLE_INTERVAL_MINUTES} minutos...", "SLEEP")
                time.sleep(CYCLE_INTERVAL_MINUTES * 60)

        except KeyboardInterrupt:
            log("Loop interrompido pelo utilizador", "INFO")
            self.is_running = False

    def _run_cycle(self):
        """Executa um ciclo completo de autonomia."""
        self.cycle_count += 1
        log(f"═══ CICLO #{self.cycle_count} ═══", "WAKE")

        tasks_done_this_cycle = []
        task = get_next_task()

        if not task:
            log("Backlog vazio — a fazer brainstorm autónomo", "BRAINSTORM")
            if self.cycle_count % BRAINSTORM_INTERVAL_CYCLES == 0:
                ideas = autonomous_brainstorm(self.orchestrator)
                if ideas:
                    self._notify_joel(
                        f"💡 Brainstorm autónomo:\n" +
                        "\n".join(f"• {i.get('title', '?')}" for i in ideas)
                    )
            return

        # Executar tarefas do backlog
        tasks_attempted = 0
        while task and tasks_attempted < MAX_TASKS_PER_CYCLE:
            tasks_attempted += 1
            log(f"A trabalhar em: '{task['title']}'", "INFO")

            success, result = self._execute_task(task)

            if success:
                mark_task_done(task["id"], result)
                self.tasks_completed += 1
                tasks_done_this_cycle.append(f"✅ {task['title']}")
                log(f"Tarefa concluída: '{task['title']}'", "SUCCESS")
            else:
                mark_task_failed(task["id"], result)
                tasks_done_this_cycle.append(f"❌ {task['title']} — {result}")
                log(f"Tarefa falhou: '{task['title']}' — {result}", "ERROR")

            task = get_next_task()

        # Relatório para o Joel
        if tasks_done_this_cycle:
            report = (
                f"📊 Relatório — Ciclo #{self.cycle_count}\n\n" +
                "\n".join(tasks_done_this_cycle) +
                f"\n\nTotal concluídas: {self.tasks_completed}"
            )
            self._notify_joel(report)

    def _execute_task(self, task: dict) -> tuple[bool, str]:
        """
        Executa uma tarefa. Integra com o orchestrator real.
        Retorna (sucesso, resultado).
        """
        if self.orchestrator:
            try:
                result = self.orchestrator.execute(task["description"])
                return True, str(result)
            except Exception as e:
                return False, str(e)
        else:
            # Modo simulação (sem orchestrator)
            log(f"[SIMULAÇÃO] Executaria: {task['description']}", "INFO")
            time.sleep(2)
            return True, "Executado em modo simulação"

    def _notify_joel(self, message: str):
        """Envia mensagem ao Joel via Telegram."""
        if self.telegram_bot:
            try:
                JOEL_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID", "1094139387")
                self.telegram_bot.send_message(JOEL_TELEGRAM_ID, message)
                log(f"Telegram enviado ao Joel", "INFO")
            except Exception as e:
                log(f"Erro ao enviar Telegram: {e}", "ERROR")
        else:
            log(f"[TELEGRAM] {message}", "INFO")

    def pause(self):
        """Pausar o loop (via comando Telegram do Joel)."""
        self.paused = True
        log("Loop pausado pelo Joel", "INFO")

    def resume(self):
        """Retomar o loop."""
        self.paused = False
        log("Loop retomado", "INFO")

    def add_priority_task(self, title: str, description: str):
        """Joel adiciona tarefa urgente pelo Telegram (prioridade máxima)."""
        task = add_to_backlog(title, description, priority=1, source="joel_telegram")
        log(f"Tarefa urgente adicionada pelo Joel: '{title}'", "INFO")
        return task

    def status(self) -> str:
        """Retorna status atual do sistema para o Joel."""
        backlog = load_backlog()
        pending = [t for t in backlog if t["status"] == "pending"]
        return (
            f"🤖 Status do Sistema\n"
            f"Ciclos executados: {self.cycle_count}\n"
            f"Tarefas concluídas: {self.tasks_completed}\n"
            f"Tarefas no backlog: {len(pending)}\n"
            f"Próximo ciclo em: {CYCLE_INTERVAL_MINUTES} min\n"
            f"Pausado: {'Sim' if self.paused else 'Não'}"
        )


# ─── INTEGRAÇÃO COM main.py ────────────────────────────────────────────────────

def integrate_with_main(orchestrator=None, telegram_bot=None):
    """
    Chamar esta função no main.py para ativar a autonomia.
    
    Exemplo de uso em main.py:
    
        from autonomous_loop import integrate_with_main
        
        # No fim do main, após inicializar orchestrator e bot:
        integrate_with_main(
            orchestrator=my_orchestrator,
            telegram_bot=my_bot
        )
    """
    loop = AutonomousLoop(
        orchestrator=orchestrator,
        telegram_bot=telegram_bot,
    )

    # Adicionar comandos Telegram para controlo
    if telegram_bot:
        _register_telegram_commands(telegram_bot, loop)

    # Seed inicial do backlog se estiver vazio
    if not load_backlog():
        _seed_initial_backlog()

    # Iniciar loop (bloqueia aqui)
    loop.start()
    return loop


def _register_telegram_commands(bot, loop: AutonomousLoop):
    """Regista comandos no bot do Telegram para o Joel controlar o sistema."""
    # Estes handlers devem ser adaptados ao framework do bot usado
    commands = {
        "/status":  lambda: loop.status(),
        "/pausar":  lambda: (loop.pause(), "⏸️ Sistema pausado."),
        "/retomar": lambda: (loop.resume(), "▶️ Sistema retomado."),
        "/backlog": lambda: _format_backlog(),
        # Joel pode adicionar tarefa: /tarefa Título | Descrição
    }
    log(f"Comandos Telegram registados: {', '.join(commands.keys())}", "INFO")
    return commands


def _format_backlog() -> str:
    backlog = load_backlog()
    pending = [t for t in backlog if t["status"] == "pending"]
    if not pending:
        return "📭 Backlog vazio — a fazer brainstorm!"
    lines = ["📋 Backlog atual:\n"]
    for i, t in enumerate(pending[:10], 1):
        lines.append(f"{i}. [{t['priority']}] {t['title']}")
    return "\n".join(lines)


def _seed_initial_backlog():
    """Popula o backlog com tarefas iniciais de setup."""
    initial_tasks = [
        ("Verificar integridade do sistema",
         "Verificar todos os ficheiros críticos, logs recentes e estado do git", 1),
        ("Melhorar sistema de logs",
         "Implementar logs estruturados com níveis e rotação automática", 4),
        ("Adicionar testes ao orchestrator",
         "Criar testes unitários básicos para o orchestrator principal", 5),
        ("Documentar APIs internas",
         "Gerar documentação automática dos módulos principais", 6),
        ("Otimizar uso de tokens",
         "Analisar e reduzir tokens usados por ciclo de LLM", 4),
    ]
    for title, desc, priority in initial_tasks:
        add_to_backlog(title, desc, priority, source="seed_inicial")
    log(f"Backlog inicializado com {len(initial_tasks)} tarefas", "INFO")


# ─── PONTO DE ENTRADA STANDALONE ──────────────────────────────────────────────

if __name__ == "__main__":
    print("A iniciar loop autónomo em modo standalone (sem LLM)...")
    print("Ctrl+C para parar.\n")
    loop = AutonomousLoop()
    _seed_initial_backlog()
    loop.start()
