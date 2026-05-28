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
SELF_IMPROVE_INTERVAL_CYCLES = 10  # Batch 9: auto-análise a cada N ciclos
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


def _detect_workflow(task: dict) -> str | None:
    """
    Detecta automaticamente se uma tarefa deve usar um workflow template.
    Retorna o nome do template ou None para execução directa.

    Batch 5 — heurísticas locais, zero chamadas API.
    """
    title = (task.get("title") or "").lower()
    desc  = (task.get("description") or "").lower()
    text  = f"{title} {desc}"

    # Keywords → bug_fix
    BUG_KEYWORDS = {"bug", "fix", "erro", "error", "crash", "falha", "broken",
                    "não funciona", "nao funciona", "traceback", "exception"}
    if any(kw in text for kw in BUG_KEYWORDS):
        return "bug_fix"

    # Keywords → dev_cycle
    DEV_KEYWORDS = {"implementa", "implement", "feature", "adiciona", "cria módulo",
                    "cria ficheiro", "criar ficheiro", "nova funcionalidade",
                    "refactor", "refactori", "migra", "upgrade"}
    if any(kw in text for kw in DEV_KEYWORDS):
        return "dev_cycle"

    # Keywords → research
    RESEARCH_KEYWORDS = {"investiga", "research", "analisa", "documenta",
                         "explora", "pesquisa", "audit", "auditoria"}
    if any(kw in text for kw in RESEARCH_KEYWORDS):
        return "research"

    # Complexidade por comprimento: descrições muito longas → dev_cycle
    if len(desc) > 300:
        return "dev_cycle"

    return None  # Execução directa para tarefas simples



def add_to_backlog(title: str, description: str = "", priority: int = 5, source: str = "manual") -> dict:
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
            retry_count = task.get("retry_count", 0)
            max_retries = task.get("max_retries", 2)

            if retry_count < max_retries:
                # Ainda há tentativas disponíveis — voltar para pending com contador
                task["status"]      = "pending"
                task["retry_count"] = retry_count + 1
                task["last_error"]  = reason
                task["last_retry"]  = datetime.now().isoformat()
                # Aumentar prioridade ligeiramente para não ficar no fundo
                task["priority"]    = min(task.get("priority", 5) + 1, 9)
            else:
                # Esgotou retries — falha definitiva
                task["status"]     = "failed"
                task["failed_at"]  = datetime.now().isoformat()
                task["reason"]     = reason
                task["retry_count"] = retry_count
    save_backlog(backlog)


def mark_task_needs_retry(task_id: str, reason: str = ""):
    """Marca uma tarefa como precisando de retry imediato (sem consumir contador)."""
    backlog = load_backlog()
    for task in backlog:
        if task["id"] == task_id:
            task["status"]     = "pending"
            task["last_error"] = reason
            task["priority"]   = max(task.get("priority", 5) - 1, 1)  # sobe prioridade
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
    Sessão de brainstorm autónomo com LLM real (DeepSeek).
    Chama _call_llm() directamente — não depende do orchestrator.
    Fallback para lista local se API indisponível.
    """
    log("Sessão de brainstorm autónomo iniciada", "BRAINSTORM")
    ideas = []

    # Contexto actual do sistema para brainstorm relevante
    backlog_all     = load_backlog()
    backlog_pending = [t for t in backlog_all if t.get("status") == "pending"]
    backlog_failed  = [t for t in backlog_all if t.get("status") == "failed"]

    context_lines = []
    if backlog_pending:
        context_lines.append("Tarefas pendentes ({}): {}".format(
            len(backlog_pending),
            ", ".join(t["title"] for t in backlog_pending[:3])
        ))
    if backlog_failed:
        context_lines.append("Tarefas falhadas ({}): {}".format(
            len(backlog_failed),
            ", ".join(t["title"] for t in backlog_failed[:3])
        ))
    try:
        log_path = MEMORY_DIR / "autonomous_log.md"
        if log_path.exists():
            recent_log = log_path.read_text(encoding="utf-8", errors="ignore")[-600:]
            last_lines = [l for l in recent_log.split("\n") if l.strip()][-4:]
            context_lines.append("Log recente:\n" + "\n".join(last_lines))
    except Exception:
        pass

    context = "\n".join(context_lines) if context_lines else "Sistema em estado inicial."

    prompt = """És o Supervisor do ecossistema agentsbot — agentes IA que trabalham em conjunto para construir e melhorar o próprio sistema.

Estado actual:
{}

Agentes disponíveis: developer, arquiteto, qa_tester, explorador, documentador, auto_fixer, auto_optimizer, devops, auto_evolver.

Gera 3 tarefas concretas e implementáveis para o sistema evoluir agora.
Cada tarefa deve ser específica, achievable num ciclo, e aumentar a autonomia ou qualidade do sistema.

Responde APENAS com JSON válido, sem markdown, sem explicações:
[{{"title": "título curto", "description": "o que fazer exactamente em detalhe", "priority": 5, "agent": "nome_do_agente"}}]""".format(context)

    try:
        from agents.llm_agent import _call_llm
        response = _call_llm(
            messages=[{"role": "user", "content": prompt}],
            use_tools=False,
            max_tokens=600,
        )
        raw = response["choices"][0]["message"].get("content", "[]").strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        ideas = json.loads(raw)
        log("Brainstorm gerou {} ideias via LLM real".format(len(ideas)), "BRAINSTORM")
    except Exception as e:
        log("Brainstorm LLM falhou ({}), usando fallback".format(e), "ERROR")
        ideas = _brainstorm_fallback()
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
                retry_count = task.get("retry_count", 0)
                max_retries = task.get("max_retries", 2)
                mark_task_failed(task["id"], result)
                if retry_count < max_retries:
                    tasks_done_this_cycle.append(
                        f"🔄 {task['title']} — retry {retry_count + 1}/{max_retries}"
                    )
                    log(
                        f"Tarefa agendada para retry ({retry_count + 1}/{max_retries}): "
                        f"'{task['title']}'",
                        "INFO"
                    )
                else:
                    tasks_done_this_cycle.append(f"❌ {task['title']} — {result}")
                    log(f"Tarefa falhou definitivamente: '{task['title']}' — {result}", "ERROR")

            task = get_next_task()

        # Relatório para o Joel
        if tasks_done_this_cycle:
            report = (
                f"📊 Relatório — Ciclo #{self.cycle_count}\n\n" +
                "\n".join(tasks_done_this_cycle) +
                f"\n\nTotal concluídas: {self.tasks_completed}"
            )
            self._notify_joel(report)

        # Batch 9: Self-Improvement Loop — a cada N ciclos
        if self.cycle_count % SELF_IMPROVE_INTERVAL_CYCLES == 0:
            self._run_self_improvement()

    def _run_self_improvement(self):
        """
        Batch 9 — Self-Improvement Loop.

        A cada SELF_IMPROVE_INTERVAL_CYCLES ciclos:
        1. Analisa logs de falhas (local, sem API)
        2. Propõe melhorias (1 chamada DeepSeek para casos complexos)
        3. Gera patches para melhorias simples
        4. Valida patches (sintaxe, search_str)
        5. Regista no changelog_auto.md
        """
        log(f"[Self-Improve] A iniciar ciclo de auto-análise (ciclo #{self.cycle_count})", "INFO")
        try:
            from evolution.log_analyzer import LogAnalyzer
            from evolution.improvement_proposer import ImprovementProposer
            from evolution.patch_generator import PatchGenerator
            from evolution.patch_validator import PatchValidator

            # 1. Analisar logs
            analyzer = LogAnalyzer()
            report = analyzer.analyze(days_back=7)
            total_eps = report["totals"]["total_episodes"]
            failure_rate = report["totals"]["failure_rate"]
            n_suggestions = len(report["suggestions"])

            log(
                f"[Self-Improve] Análise: {total_eps} episódios, "
                f"taxa falha {failure_rate*100:.0f}%, "
                f"{n_suggestions} sugestões",
                "INFO"
            )

            if n_suggestions == 0:
                log("[Self-Improve] Sistema saudável — sem sugestões de melhoria", "INFO")
                return

            # 2. Propor melhorias
            proposer = ImprovementProposer()
            proposals = proposer.propose(report, use_llm=True)

            # 3. Gerar e validar patches para propostas simples
            generator = PatchGenerator()
            validator = PatchValidator()
            applied_patches = []

            for proposal in proposals:
                if proposal.get("complexity") != "low":
                    continue  # Patches complexos requerem revisão humana

                patch = generator.generate(proposal, use_llm=False)
                if not patch:
                    continue

                validation = validator.validate(patch)
                if not validation["valid"]:
                    log(
                        f"[Self-Improve] Patch rejeitado para '{proposal['title']}': "
                        f"{validation['errors']}",
                        "WARNING"
                    )
                    continue

                # Aplicar patch
                result = validator.apply(patch, dry_run=False)
                if result["success"]:
                    applied_patches.append({
                        "title": proposal["title"],
                        "file": patch["target_file"],
                        "backup": result.get("backup_path", ""),
                    })
                    log(f"[Self-Improve] Patch aplicado: {proposal['title']}", "SUCCESS")

            # 4. Registar no changelog
            self._update_changelog(report, proposals, applied_patches)

            # 5. Notificar se houver algo relevante
            if proposals or applied_patches:
                msg = (
                    f"🧬 Self-Improvement Ciclo #{self.cycle_count}\n"
                    f"Análise: {total_eps} episódios, falha {failure_rate*100:.0f}%\n"
                    f"Propostas: {len(proposals)} | Patches aplicados: {len(applied_patches)}"
                )
                if applied_patches:
                    msg += "\n" + "\n".join(f"  ✅ {p['title']}" for p in applied_patches)
                self._notify_joel(msg)

        except Exception as e:
            log(f"[Self-Improve] Erro no ciclo de auto-melhoria: {e}", "ERROR")

    def _update_changelog(self, report: dict, proposals: list, applied: list):
        """Actualiza o changelog automático de melhorias."""
        from datetime import datetime
        changelog_path = Config.REPO_LOCAL_PATH / "evolution" / "changelog_auto.md"
        if not changelog_path.exists():
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entries = []

        for p in proposals[:5]:
            entry = (
                f"\n### [{now}] {p['title']}\n"
                f"- **Tipo**: {p['source']}\n"
                f"- **Prioridade**: {p['priority']}\n"
                f"- **Ficheiros**: {', '.join(p.get('target_files', ['?']))}\n"
                f"- **Descrição**: {p['description']}\n"
            )
            # Marcar se foi aplicado
            was_applied = any(a["title"] == p["title"] for a in applied)
            entry += f"- **Status**: {'✅ Aplicado' if was_applied else '📋 Proposto (revisão manual)'}\n"
            entries.append(entry)

        if entries:
            content = changelog_path.read_text(encoding="utf-8")
            marker = "<!-- As entradas são inseridas automaticamente abaixo desta linha -->"
            new_section = marker + "\n" + "\n".join(entries)
            updated = content.replace(marker, new_section, 1)
            changelog_path.write_text(updated, encoding="utf-8")

    def _execute_task(self, task: dict) -> tuple[bool, str]:
        """
        Executa uma tarefa.

        Batch 5 — State Graphs:
        Tarefas complexas (com campo 'workflow' ou keywords de complexidade)
        são roteadas para um workflow template em vez de execução directa.
        Retorna (sucesso, resultado).
        """
        # ── Routing por workflow (Batch 5) ──────────────────────────────────────
        workflow_name = task.get("workflow")
        if not workflow_name:
            workflow_name = _detect_workflow(task)

        if workflow_name:
            return self._execute_via_workflow(task, workflow_name)

        # ── Execução directa (comportamento original) ───────────────────────────
        if self.orchestrator:
            try:
                result = self.orchestrator.execute(task["description"])
                return True, str(result)
            except Exception as e:
                return False, str(e)
        else:
            log(f"[SIMULAÇÃO] Executaria: {task['description']}", "INFO")
            time.sleep(2)
            return True, "Executado em modo simulação"

    def _execute_via_workflow(self, task: dict, workflow_name: str) -> tuple[bool, str]:
        """
        Executa uma tarefa complexa via StateMachine com workflow template.
        Cada passo do workflow é executado pelo orchestrator.
        """
        log(f"[Workflow] Tarefa '{task['title']}' → workflow '{workflow_name}'", "INFO")

        try:
            from pipelines.state_machine import StateMachine, RunState

            sm = StateMachine.from_yaml(workflow_name)

            # Executor: cada passo do workflow delega ao orchestrator
            def step_executor(step_def, run):
                # Renderizar template com contexto disponível
                template = step_def.task_template
                ctx = {**run.context}
                # Substituir placeholders simples {key}
                for k, v in ctx.items():
                    template = template.replace(f"{{{k}}}", str(v)[:500])
                # Fallback: task_short se não definido
                template = template.replace("{task_short}", run.context.get("task", "")[:60])
                template = template.replace("{task_slug}", run.context.get("task", "")
                                            .lower().replace(" ", "_")[:40])

                if self.orchestrator:
                    return str(self.orchestrator.execute(template))
                else:
                    log(f"[Workflow/SIM] {step_def.name}: {template[:80]}", "INFO")
                    return f"[sim] {step_def.name} concluído"

            sm.set_executor(step_executor)

            context = {
                "task": task.get("description", task.get("title", "")),
                "task_title": task.get("title", ""),
            }
            run_id = sm.start(context=context)

            # Executar passo a passo (síncrono)
            max_ticks = len(sm.definition.steps) * 4
            for _ in range(max_ticks):
                run = sm.tick(run_id)
                if run.state in (RunState.COMPLETED, RunState.FAILED):
                    break

            summary = sm.summary(run_id)
            log(f"[Workflow] Run {run_id} → {run.state}", "INFO")

            if run.state == RunState.COMPLETED:
                return True, summary
            else:
                return False, f"Workflow falhou:\n{summary}\nErro: {run.error}"

        except FileNotFoundError:
            log(f"[Workflow] Template '{workflow_name}' não encontrado — execução directa", "WARN")
            # Fallback para execução directa
            if self.orchestrator:
                try:
                    result = self.orchestrator.execute(task["description"])
                    return True, str(result)
                except Exception as e:
                    return False, str(e)
            return True, "Executado em modo fallback (sem workflow)"
        except Exception as e:
            log(f"[Workflow] Erro: {e}", "ERROR")
            return False, str(e)

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
