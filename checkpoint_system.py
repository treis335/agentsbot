"""
checkpoint_system.py
Sistema de checkpoint para execuções longas.
Guarda estado a cada passo e permite retomar de onde parou.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path


MEMORY_DIR = Path("memory")
CHECKPOINT_FILE = MEMORY_DIR / "checkpoint.json"
CURRENT_TASK_FILE = MEMORY_DIR / "current_task.md"


def ensure_memory_dir():
    """Garante que o diretório memory/ existe."""
    MEMORY_DIR.mkdir(exist_ok=True)


# --- GUARDAR CHECKPOINT --------------------------------------------------------

def save_checkpoint(task: str, step: int, state: dict, next_action: str,
                    files_modified: list = None):
    """
    Guarda o estado atual da execução.

    Args:
        task:           Descrição da tarefa atual
        step:           Número do passo atual (começa em 1)
        state:          Dicionário com qualquer estado relevante
        next_action:    Descrição do próximo passo a executar
        files_modified: Lista de ficheiros modificados até agora
    """
    ensure_memory_dir()

    checkpoint = {
        "task": task,
        "step": step,
        "state": state,
        "next_action": next_action,
        "files_modified": files_modified or [],
        "timestamp": datetime.now().isoformat(),
        "session_id": _get_or_create_session_id(),
    }

    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    print(f"[SALVAR] Checkpoint guardado ? tarefa: '{task}' | passo: {step}")
    return checkpoint


# --- CARREGAR CHECKPOINT -------------------------------------------------------

def load_checkpoint() -> dict | None:
    """
    Carrega o último checkpoint guardado.
    Retorna None se não existir checkpoint.
    """
    if not CHECKPOINT_FILE.exists():
        return None

    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)

    print(f"[PASTA] Checkpoint encontrado:")
    print(f"   Tarefa:      {checkpoint['task']}")
    print(f"   Passo:       {checkpoint['step']}")
    print(f"   Pr?xima a??o: {checkpoint['next_action']}")
    print(f"   Guardado em: {checkpoint['timestamp']}")
    return checkpoint


# --- LIMPAR CHECKPOINT ---------------------------------------------------------

def clear_checkpoint():
    """Remove o checkpoint após tarefa concluída com sucesso."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("[OK] Checkpoint limpo ? tarefa conclu?da.")


# --- GESTOR DE ITERAÇÕES -------------------------------------------------------

class IterationManager:
    """
    Controla o número de iterações e guarda checkpoint
    automaticamente para evitar perda de trabalho quando
    o ambiente corta a execução.
    """

    def __init__(self, task: str, max_iterations: int = 50,
                 checkpoint_every: int = 5):
        """
        Args:
            task:               Descrição da tarefa
            max_iterations:     Limite de segurança (nunca exceder)
            checkpoint_every:   Guardar checkpoint a cada N iterações
        """
        self.task = task
        self.max_iterations = max_iterations
        self.checkpoint_every = checkpoint_every
        self.current_step = 0
        self.state = {}
        self.files_modified = []
        self._start_time = time.time()

        ensure_memory_dir()
        print(f"[START] IterationManager iniciado ? tarefa: '{task}'")
        print(f"   Max itera??es: {max_iterations} | Checkpoint cada: {checkpoint_every}")

    def tick(self, next_action: str = "", state_update: dict = None) -> bool:
        """
        Avança uma iteração. Deve ser chamado no início de cada passo do loop.

        Args:
            next_action:  Descrição do que vai acontecer neste passo
            state_update: Dicionário com atualizações ao estado (merge)

        Returns:
            True se pode continuar, False se atingiu o limite.
        """
        self.current_step += 1

        # Atualizar estado
        if state_update:
            self.state.update(state_update)

        # Verificar limite
        if self.current_step >= self.max_iterations:
            save_checkpoint(
                task=self.task,
                step=self.current_step,
                state=self.state,
                next_action=next_action or "LIMITE ATINGIDO — retomar aqui",
                files_modified=self.files_modified,
            )
            elapsed = round(time.time() - self._start_time, 1)
            print(f"\n[!]  Limite de {self.max_iterations} itera??es atingido ap?s {elapsed}s.")
            print(f"   Checkpoint guardado. Para retomar, executar novamente o script.")
            return False

        # Checkpoint periódico
        if self.current_step % self.checkpoint_every == 0:
            save_checkpoint(
                task=self.task,
                step=self.current_step,
                state=self.state,
                next_action=next_action,
                files_modified=self.files_modified,
            )

        return True

    def add_file(self, filepath: str):
        """Regista um ficheiro como modificado nesta sessão."""
        if filepath not in self.files_modified:
            self.files_modified.append(filepath)

    def done(self):
        """Chamar quando a tarefa termina com sucesso."""
        elapsed = round(time.time() - self._start_time, 1)
        print(f"\n[OK] Tarefa '{self.task}' conclu?da em {self.current_step} passos ({elapsed}s).")
        clear_checkpoint()
        _update_current_task("Concluída", self.task)


# --- ANTI-LOOP HANDLER ---------------------------------------------------------

class AntiLoopGuard:
    """
    Deteta ações repetidas e impede loops infinitos.
    Regista erros em memory/errors.md.
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._action_counts: dict[str, int] = {}
        self._errors_file = MEMORY_DIR / "errors.md"

    def check(self, action_key: str, context: str = "") -> bool:
        """
        Verifica se uma ação foi tentada demasiadas vezes.

        Args:
            action_key: Identificador único da ação (ex: "git_push", "fix_bug_42")
            context:    Contexto adicional para o log de erros

        Returns:
            True se pode tentar, False se deve parar.
        """
        count = self._action_counts.get(action_key, 0) + 1
        self._action_counts[action_key] = count

        if count > self.max_retries:
            self._log_error(action_key, count, context)
            print(f"\n[ALARME] ANTI-LOOP: '{action_key}' falhou {count}x. A parar.")
            print(f"   Erro registado em {self._errors_file}")
            print(f"   Contexto: {context}")
            return False

        if count > 1:
            print(f"[!]  Tentativa {count}/{self.max_retries} para '{action_key}'")

        return True

    def reset(self, action_key: str):
        """Resetar contador após sucesso."""
        self._action_counts.pop(action_key, None)

    def _log_error(self, action_key: str, count: int, context: str):
        ensure_memory_dir()
        entry = (
            f"\n---\n"
            f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**A??o:** `{action_key}`\n"
            f"**Tentativas:** {count}\n"
            f"**Contexto:** {context or 'N/A'}\n"
            f"**Status:** Escalado para utilizador\n"
        )
        with open(self._errors_file, "a", encoding="utf-8") as f:
            f.write(entry)


# --- UTILITÁRIOS INTERNOS ------------------------------------------------------

def _get_or_create_session_id() -> str:
    session_file = MEMORY_DIR / ".session_id"
    if session_file.exists():
        return session_file.read_text().strip()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    ensure_memory_dir()
    session_file.write_text(session_id)
    return session_id


def _update_current_task(status: str, description: str):
    ensure_memory_dir()
    content = (
        f"# Tarefa Atual\n\n"
        f"**Status:** {status}\n"
        f"**Descri??o:** {description}\n"
        f"**?ltima atualiza??o:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    CURRENT_TASK_FILE.write_text(content, encoding="utf-8")


# --- EXEMPLO DE USO ------------------------------------------------------------

if __name__ == "__main__":
    # Verificar se há checkpoint para retomar
    cp = load_checkpoint()
    start_step = cp["step"] if cp else 0

    # Iniciar gestor de iterações
    mgr = IterationManager(
        task="Exemplo de tarefa longa",
        max_iterations=20,
        checkpoint_every=3,
    )
    guard = AntiLoopGuard(max_retries=3)

    # Loop principal (exemplo)
    items = list(range(start_step, 15))
    for i, item in enumerate(items):
        action_key = f"process_item_{item}"

        if not guard.check(action_key, context=f"A processar item {item}"):
            print("Loop detetado ? a parar.")
            break

        if not mgr.tick(
            next_action=f"Processar item {item + 1}",
            state_update={"last_item": item}
        ):
            print("Limite de itera??es ? script vai ser reiniciado.")
            break

        # Simular trabalho
        print(f"  -> Passo {mgr.current_step}: a processar item {item}")
        guard.reset(action_key)

    else:
        mgr.done()
