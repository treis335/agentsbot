"""
autonomous_loop.py
Motor de autonomia do ecossistema — ciclo autónomo, watchdog, cognição.
"""

import asyncio
import json
import os
import sys
import time
import threading
import random
from datetime import datetime
from pathlib import Path
from core.cognitive_cycle import CognitiveCycle

# --- CONFIGURAÇÃO --------------------------------------------------------------
CYCLE_INTERVAL_SECONDS = 10
MAX_TASKS_PER_CYCLE = 1
MEMORY_DIR = Path("memory")
BACKLOG_FILE = MEMORY_DIR / "backlog.json"
LOG_FILE = MEMORY_DIR / "autonomous_log.md"
REBOOT_FLAG = "auto_reboot.flag"


# --- BACKLOG -------------------------------------------------------------------
def load_backlog() -> list:
    MEMORY_DIR.mkdir(exist_ok=True)
    if not BACKLOG_FILE.exists():
        return []
    try:
        with open(BACKLOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_backlog(backlog: list):
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(BACKLOG_FILE, "w", encoding="utf-8") as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)


def _seed_initial_backlog():
    """Cria backlog inicial se não existir"""
    MEMORY_DIR.mkdir(exist_ok=True)
    if not BACKLOG_FILE.exists():
        initial = [
            {"id": "onboarding", "desc": "Configurar ambiente inicial do agente", "status": "pending"},
            {"id": "self_check", "desc": "Verificar saude do sistema e dependencias", "status": "pending"},
            {"id": "first_task", "desc": "Executar primeira tarefa de teste", "status": "pending"}
        ]
        save_backlog(initial)
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except (ValueError, AttributeError):
            pass
        try:
            print("[Seed] Backlog inicial criado")
        except UnicodeEncodeError:
            print("[Seed] Backlog inicial criado".encode('utf-8', errors='replace').decode('utf-8'))


# --- LOG -----------------------------------------------------------------------
def log_cycle(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (ValueError, AttributeError):
        pass
    try:
        print(line)
    except UnicodeEncodeError:
        safe_line = line.encode('utf-8', errors='replace').decode('utf-8')
        print(safe_line)
    MEMORY_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# --- CLASSE PRINCIPAL ---------------------------------------------------------
def _evaluate_result(result: str) -> bool:
    """
    Avalia se o resultado de um agente é realmente um sucesso.
    Um LLM nunca lança excepção — mas pode responder "não consegui".
    Retorna False se o resultado indica falha real.
    """
    if not result or not result.strip():
        return False
    r = result.lower()
    # Sinais de falha no texto
    failure_signals = [
        "peço desculpa", "peco desculpa",
        "houve um erro técnico", "houve um erro tecnico",
        "não consegui", "nao consegui",
        "cannot schedule new futures",
        "cannot write", "erro ao escrever",
        "traceback (most recent",
        "exception:", "error:",
        "❌ erro", "❌ falha",
        "não foi possível", "nao foi possivel",
        "infelizmente não", "infelizmente nao",
        "desculpe, não", "desculpe, nao",
    ]
    for signal in failure_signals:
        if signal in r:
            return False
    # Resultado muito curto pode ser resposta vazia/inútil
    if len(result.strip()) < 20:
        return False
    return True


class AutonomousLoop:
    def __init__(self, orchestrator=None, telegram_bot=None):
        self.orchestrator = orchestrator
        self.telegram_bot = telegram_bot
        self.running = False
        self.thread = None
        self.cycle_count = 0

        # Batch 9 — Self-Improvement Loop
        try:
            from evolution.self_improvement_loop import SelfImprovementLoop
            self._self_improve = SelfImprovementLoop(telegram_bot=telegram_bot)
            log_cycle("[SelfImprove] Loop de auto-melhoria iniciado [OK]")
        except Exception as e:
            self._self_improve = None

        # CognitiveCycle — Pensar -> Agir -> Observar -> Aprender -> Evoluir
        try:
            self._cognitive = CognitiveCycle()
            log_cycle("[Cognitive] Ciclo cognitivo iniciado [OK]")
        except Exception as e:
            self._cognitive = None
            log_cycle(f"[Cognitive] Indisponivel: {e}")
            log_cycle(f"[SelfImprove] Indispon?vel: {e}")

    def start(self):
        """Inicia o loop autonomo em background"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="AutonomousLoop"
        )
        self.thread.start()
        log_cycle("AutonomousLoop iniciado em background")

    def stop(self):
        """Para o loop"""
        self.running = False
        log_cycle("AutonomousLoop parado")

    def _run_loop(self):
        """Loop principal — corre para sempre"""
        log_cycle("=" * 50)
        log_cycle("LOOP AUTONOMO INICIADO")
        log_cycle(f"Ciclo a cada {CYCLE_INTERVAL_SECONDS}s")
        log_cycle("=" * 50)

        while self.running:
            try:
                self._run_cycle()
            except Exception as e:
                log_cycle(f"[ERRO] No ciclo: {e}")
            time.sleep(CYCLE_INTERVAL_SECONDS)

    def _run_cycle(self):
        """Um ciclo completo do loop autonomo — executa tarefas reais via LLMAgent."""
        self.cycle_count += 1
        cycle_id = self.cycle_count
        log_cycle(f"[Ciclo #{cycle_id}] Inicio")

        # 0. Ciclo Cognitivo - Pensar -> Agir -> Observar -> Aprender -> Evoluir
        if self._cognitive:
            try:
                # NOTA: task_desc pode nao estar definida ainda (definida mais abaixo)
                ctx = task_desc if "task_desc" in dir() and task_desc else "ciclo_autonomo"
                cog_result = self._cognitive.run_cycle(context=ctx)
                if cog_result.get("loop_detected"):
                    log_cycle("[Cognitive] Loop detetado - a mudar de abordagem")
                    # Forcar fallback para evitar repeticao
                    if "task_desc" in dir() and task_desc:
                        task_desc = f"{task_desc} (tenta uma abordagem completamente diferente)"
                log_cycle(f"[Cognitive] Ciclo #{cog_result.get('cycle', '?')} concluido")
            except Exception as e:
                log_cycle(f"[Cognitive] Erro: {e}")

        # 1. Verificar reboot
        if os.path.exists(REBOOT_FLAG):
            log_cycle("[REBOOT] Sinal detetado! A reiniciar...")
            try:
                os.remove(REBOOT_FLAG)
            except:
                pass
            time.sleep(0.5)
            os.execv(sys.executable, [sys.executable, "main.py"])
            return

        # 2. Carregar backlog
        backlog = load_backlog()

        # 3. Filtrar tarefas pendentes
        pending = [t for t in backlog if t.get("status") in ("pending", "")]
        if not pending:
            log_cycle("[Ciclo] Sem tarefas pendentes — a gerar novas...")
            self._generate_new_tasks(backlog)
            return

        # 4. Escolher tarefa por prioridade (campo priority ou primeira)
        task = sorted(pending, key=lambda t: -int(t.get("priority", 5)))[0]
        task_id  = task.get("id", "unknown")
        task_desc = task.get("desc", task.get("task", task.get("title", "Tarefa sem descricao")))
        log_cycle(f"[Ciclo #{cycle_id}] Tarefa: {task_desc[:80]}")

        # 5. Marcar como em execução
        for t in backlog:
            if t.get("id") == task_id:
                t["status"] = "running"
                t["started_at"] = datetime.now().isoformat()
                break
        save_backlog(backlog)

        # 6. Executar via LLMAgent (execução real)
        success, result_text = self._execute_task_real(task_desc, task_id)

        # 7. Actualizar backlog com resultado
        status = "completed" if success else "failed"
        for t in backlog:
            if t.get("id") == task_id:
                t["status"] = status
                t["completed_at"] = datetime.now().isoformat()
                t["result"] = str(result_text)[:500]
                break
        save_backlog(backlog)
        log_cycle(f"[Ciclo #{cycle_id}] {'[OK]' if success else '[X]'} {task_desc[:60]} -> {status}")

        # 7b. Notificações proactivas
        try:
            from bot.notifier import get_notifier
            notifier = get_notifier()
            if success:
                asyncio.run(notifier.task_completed(
                    title=task.get("title", task_desc[:60]),
                    agent=task.get("_last_agent", "agente"),
                    result=str(result_text),
                ))
            else:
                asyncio.run(notifier.task_failed(
                    title=task.get("title", task_desc[:60]),
                    agent=task.get("_last_agent", "agente"),
                    error=str(result_text),
                ))
            # Verificar se é hora do resumo diário
            asyncio.run(notifier.check_daily_summary())
        except Exception as _ne:
            log_cycle(f"[Notifier] {_ne}")

        # 8. Batch 9 — Self-Improvement a cada N ciclos
        if self._self_improve and self._self_improve.should_run():
            log_cycle(f"[SelfImprove] Ciclo #{cycle_id} ? a iniciar an?lise...")
            try:
                import asyncio as _asyncio
                _loop = _asyncio.new_event_loop()
                si_result = _loop.run_until_complete(self._self_improve.run_cycle())
                _loop.close()
                log_cycle(f"[SelfImprove] {si_result.summary}")
            except Exception as e:
                log_cycle(f"[SelfImprove] Erro: {e}")

    def _execute_task_real(self, task_desc: str, task_id: str) -> tuple:
        """
        Executa uma tarefa via capability routing + memória episódica.
        Antes de executar: injeta contexto de tentativas anteriores.
        Depois de executar: grava resultado na memória.
        Retorna (sucesso: bool, resultado: str).
        """
        from agents.capability_registry import get_registry
        from memory.loop_memory import get_loop_memory
        import asyncio as _asyncio

        mem = get_loop_memory()

        # 1. Escolher agente pelo capability registry
        registry = get_registry()
        chosen_agent = registry.match(task_desc, fallback="developer")
        log_cycle(f"[MultiAgent] '{chosen_agent}' -> {task_desc[:60]}")

        # 2. Obter contexto de memória episódica (tentativas anteriores)
        memory_ctx = mem.get_context_for_task(task_desc, task_id)
        if memory_ctx:
            log_cycle(f"[Memory] Contexto injectado ({len(memory_ctx)} chars)")

        # 3. Construir prompt enriquecido com memória + reflexões
        full_prompt = task_desc

        # 3a. Memória semântica
        semantic_ctx = ""
        try:
            from memory.semantic_search import search_for_prompt, get_index
            idx = get_index()
            if len(idx._docs) < 5:
                idx.rebuild()
            semantic_ctx = search_for_prompt(task_desc, top_k=4)
        except Exception as _se:
            pass  # semântica opcional

        # 3b. Reflexões de tarefas similares (Sistema de Reflexão — Batch 10)
        reflection_ctx = ""
        try:
            from agents.reflection_engine import get_reflection_engine
            ref_engine = get_reflection_engine()
            reflection_ctx = ref_engine.get_prompt_context(task_desc)
            if reflection_ctx:
                log_cycle(f"[Reflection] Contexto de reflexoes injectado")
        except Exception as _re:
            pass  # reflexão opcional

        if memory_ctx or semantic_ctx or reflection_ctx:
            full_prompt = (
                task_desc + "\n\n" +
                (reflection_ctx if reflection_ctx else "") +
                (semantic_ctx if semantic_ctx else "") +
                (memory_ctx if memory_ctx else "") +
                "\nUsa este contexto para nao repetir erros. "
                "Se algo falhou antes, experimenta abordagem diferente."
            )

        # 4. Executar
        try:
            from agents.llm_agent import LLMAgent
            agent = LLMAgent(agent_name=chosen_agent)
            _loop = _asyncio.new_event_loop()
            result = _loop.run_until_complete(
                agent.chat(user_id=0, user_message=full_prompt)
            )
            _loop.close()

            # 5. Avaliar se o resultado é realmente um sucesso (não só "sem excepção")
            result_text = str(result)
            real_success = _evaluate_result(result_text)
            if not real_success:
                log_cycle(f"[Quality] Resultado parece falha apesar de sem excepção")
            mem.record(task_id, task_desc, chosen_agent, success=real_success, result=result_text)
            try:
                from agents.reflection_engine import get_reflection_engine
                reflection = get_reflection_engine().reflect(
                    task=task_desc, result=str(result),
                    agent=chosen_agent, success=True, task_id=task_id
                )
                log_cycle(f"[Reflection] ✅ {reflection.what_worked[:60]}")
                if reflection.new_skill_triggered:
                    log_cycle(f"[Skill] 🧬 Nova skill: {reflection.new_skill_name}")
            except Exception as _re:
                pass

            # Registar na skill registry
            try:
                from skills.skill_registry import get_registry as _get_skill_reg
                skill_reg = _get_skill_reg()
                matched = skill_reg.match_task(task_desc)
                if matched:
                    skill_reg.record_execution(matched.id, success=True)
            except Exception:
                pass

            # Event log
            try:
                from core.event_logger import log_skill_execution
                log_skill_execution(chosen_agent, "task", task_desc, True, 0.0,
                                    result_preview=str(result)[:200])
            except Exception:
                pass

            log_cycle(f"[Memory] Episodio: {chosen_agent} success={real_success}")
            for t in load_backlog():
                if t.get("id") == task_id:
                    t["_last_agent"] = chosen_agent
                    break
            return real_success, result_text

        except Exception as e:
            error_str = str(e)
            mem.record(task_id, task_desc, chosen_agent, success=False, result=error_str)

            # Reflexão pós-falha — aprende com o erro
            try:
                from agents.reflection_engine import get_reflection_engine
                reflection = get_reflection_engine().reflect(
                    task_id=task_id, task_desc=task_desc,
                    agent=chosen_agent, success=False, result=error_str
                )
                log_cycle(f"[Reflection] Falha: {reflection.what_failed[:60]}")
                log_cycle(f"[Reflection] Estrategia ajustada: {reflection.adjusted_strategy[:60]}")
            except Exception as _re:
                pass

            log_cycle(f"[Memory] Episodio de falha: {e}")

            # Fallback com supervisor
            try:
                from agents.llm_agent import get_agent
                agent = get_agent()
                _loop = _asyncio.new_event_loop()
                result = _loop.run_until_complete(agent.chat(user_id=0, user_message=task_desc))
                _loop.close()
                result_text = str(result)
                real_success = _evaluate_result(result_text)
                mem.record(task_id, task_desc, "supervisor", success=real_success, result=result_text)
                return real_success, result_text
            except Exception as e2:
                mem.record(task_id, task_desc, "supervisor", success=False, result=str(e2))
                return False, str(e2)

    def _generate_new_tasks(self, backlog: list) -> None:
        """
        Quando o backlog fica vazio: os agentes debatem com LLM real (organic_mind)
        e geram novas tarefas a partir do debate colectivo.
        """
        log_cycle("[OrganicMind] Backlog vazio — a iniciar debate colectivo...")
        try:
            from agents.organic_mind import (
                generate_topics_from_context,
                collective_debate,
                save_debate,
            )

            # 1. Gerar tópico relevante para o momento
            topics = generate_topics_from_context()
            topic = topics[0] if topics else "Como evoluir o ecossistema agentsbot?"
            log_cycle(f"[OrganicMind] T?pico: {topic}")

            # 2. Debate colectivo — agentes pensam com LLM real
            debate = collective_debate(
                topic=topic,
                agents=["Explorador", "Developer", "Arquiteto", "AutoFixer", "Supervisor"]
            )

            # 3. Persistir debate
            save_debate(debate)

            # 4. Adicionar tarefas geradas ao backlog
            tasks_added = 0
            for t in debate.get("tasks", []):
                task_entry = {
                    "id": f"debate_{datetime.now().strftime('%H%M%S')}_{tasks_added}",
                    "title": t.get("title", "Tarefa do debate"),
                    "desc": t.get("description", t.get("title", "")),
                    "status": "pending",
                    "priority": int(t.get("priority", 5)),
                    "agent": t.get("agent", "developer"),
                    "created_at": datetime.now().isoformat(),
                    "source": "organic_debate",
                }
                backlog.append(task_entry)
                tasks_added += 1

            if tasks_added == 0:
                self._add_fallback_task(backlog)
            else:
                save_backlog(backlog)
                log_cycle(f"[OrganicMind] {tasks_added} tarefas geradas pelo debate")

            # 5. Notificar utilizador com resumo do debate
            self._notify_debate(debate)

        except Exception as e:
            log_cycle(f"[OrganicMind] Erro no debate: {e}")
            self._add_fallback_task(backlog)

    def _notify_debate(self, debate: dict) -> None:
        """Envia resumo do debate colectivo ao utilizador via Telegram."""
        try:
            contributions = debate.get("contributions", [])
            synthesis = debate.get("synthesis", "")
            topic = debate.get("topic", "")
            tasks = debate.get("tasks", [])

            lines = [f"[MENTE] **Debate colectivo**", f"[PIN] *{topic}*", ""]
            for c in contributions[:4]:
                agent = c["agent"]
                thought = c["thought"][:120]
                lines.append(f"**{agent}:** {thought}")

            if synthesis:
                lines.append(f"\n[ALVO] **Decis?o:** {synthesis[:200]}")
            if tasks:
                lines.append(f"\n[LISTA] **Tarefas geradas:** {len(tasks)}")
                for t in tasks[:2]:
                    lines.append(f"  ? {t.get('title', '?')}")

            msg = "\n".join(lines)

            from bot.notifier import get_notifier
            import asyncio as _asyncio
            notifier = get_notifier()
            _loop = _asyncio.new_event_loop()
            _loop.run_until_complete(notifier.send(msg))
            _loop.close()
        except Exception as e:
            log_cycle(f"[OrganicMind] Notifica??o falhou: {e}")

    def _add_fallback_task(self, backlog: list) -> None:
        """Adiciona tarefa de auto-análise quando geração automática falha."""
        import uuid
        fallback_tasks = [
            "Analisa os logs de execução e identifica os 3 principais problemas. Propõe soluções e implementa a mais simples.",
            "Revê o código dos agentes e melhora os system prompts para serem mais eficazes.",
            "Verifica o estado do ecossistema, corre git status e faz commit de qualquer melhoria pendente.",
            "Analisa a memória episódica e extrai lições para melhorar futuras execuções.",
            "Cria um novo agente especializado numa área que o ecossistema ainda não cobre bem.",
        ]
        import random
        desc = random.choice(fallback_tasks)
        task = {
            "id": f"auto_{uuid.uuid4().hex[:8]}",
            "title": desc[:60],
            "desc": desc,
            "status": "pending",
            "priority": 5,
            "created_at": datetime.now().isoformat(),
            "source": "fallback",
        }
        backlog.append(task)
        save_backlog(backlog)
        log_cycle(f"[AutoGen] Fallback: {desc[:60]}")
