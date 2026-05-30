"""
agents/retry_policy.py — Política de retry para tool calls falhadas.

Define QUANDO e COMO fazer retry, com backoff e limites por tipo de ferramenta.
Zero custo API — lógica puramente local.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuração de retry para um tipo de ferramenta."""
    max_retries:    int   = 2
    base_delay_s:   float = 1.0   # delay inicial em segundos
    backoff_factor: float = 2.0   # multiplicador por retry
    max_delay_s:    float = 10.0  # máximo delay entre retries


# --- Configurações por ferramenta --------------------------------------------

RETRY_CONFIGS: dict[str, RetryConfig] = {
    "write_file":      RetryConfig(max_retries=2, base_delay_s=0.5),
    "read_file":       RetryConfig(max_retries=2, base_delay_s=0.5),
    "run_python":      RetryConfig(max_retries=1, base_delay_s=1.0),
    "run_shell":       RetryConfig(max_retries=2, base_delay_s=1.0),
    "git_commit_push": RetryConfig(max_retries=2, base_delay_s=2.0, max_delay_s=10.0),
    "git_status":      RetryConfig(max_retries=1, base_delay_s=0.5),
    "web_search":      RetryConfig(max_retries=2, base_delay_s=2.0),
    "create_agent":    RetryConfig(max_retries=1, base_delay_s=0.5),
    "list_files":      RetryConfig(max_retries=1, base_delay_s=0.3),
    # Default para ferramentas não listadas
    "_default":        RetryConfig(max_retries=1, base_delay_s=1.0),
}

# Ferramentas que NUNCA devem fazer retry (idempotência não garantida)
NO_RETRY_TOOLS = set()   # por agora vazio — todos podem retry


@dataclass
class RetryState:
    """Estado de retry para uma tool call específica."""
    tool_name:   str
    attempt:     int = 0
    last_error:  str = ""
    last_result: str = ""
    history:     list = field(default_factory=list)

    def record_attempt(self, result: str, error: str = ""):
        self.attempt += 1
        self.last_error  = error
        self.last_result = result
        self.history.append({
            "attempt":   self.attempt,
            "result":    result[:200],
            "error":     error,
            "timestamp": datetime.now().isoformat(),
        })

    @property
    def can_retry(self) -> bool:
        if self.tool_name in NO_RETRY_TOOLS:
            return False
        cfg = RETRY_CONFIGS.get(self.tool_name, RETRY_CONFIGS["_default"])
        return self.attempt < cfg.max_retries

    @property
    def next_delay(self) -> float:
        cfg = RETRY_CONFIGS.get(self.tool_name, RETRY_CONFIGS["_default"])
        delay = cfg.base_delay_s * (cfg.backoff_factor ** (self.attempt - 1))
        return min(delay, cfg.max_delay_s)


class RetryPolicy:
    """
    Gere a política de retry para tool calls.

    Uso no executor:
        policy = RetryPolicy()
        state  = policy.new_state("run_python")

        result = await execute_tool(name, args)
        state.record_attempt(result, error="")

        if not verifier.verify(...).ok and state.can_retry:
            args = policy.adjust_args(name, args, state)
            await asyncio.sleep(state.next_delay)
            result = await execute_tool(name, args)
    """

    def new_state(self, tool_name: str) -> RetryState:
        return RetryState(tool_name=tool_name)

    def adjust_args(self, tool_name: str, args: dict, state: RetryState) -> dict:
        """
        Tenta ajustar os args para o retry baseado no erro anterior.
        Heurísticas simples — sem LLM.
        """
        adjusted = dict(args)

        if tool_name == "run_shell":
            cmd = adjusted.get("command", "")
            # Se falhou sem o cd do projecto, adiciona
            if "cd" not in cmd and state.attempt == 1:
                logger.info(f"[RetryPolicy] run_shell: a tentar adicionar cd ao comando")
                # Não alteramos para não quebrar comandos com paths absolutos
                # Apenas regista a sugestão
                pass

        if tool_name == "write_file":
            path = adjusted.get("path", "")
            # Se o path tem separadores Windows num ambiente Linux ou vice-versa
            if "\\" in path:
                adjusted["path"] = path.replace("\\", "/")
                logger.info(f"[RetryPolicy] write_file: corrigido separadores de path")

        return adjusted

    def should_escalate(self, state: RetryState) -> bool:
        """
        Decide se a falha deve ser escalada (reportada ao supervisor)
        em vez de continuar a tentar.
        """
        cfg = RETRY_CONFIGS.get(state.tool_name, RETRY_CONFIGS["_default"])
        return state.attempt >= cfg.max_retries

    def format_retry_log(self, state: RetryState) -> str:
        """Formata um resumo legível do histórico de retries."""
        lines = [f"[RetryPolicy] '{state.tool_name}' — {state.attempt} tentativa(s)"]
        for h in state.history:
            lines.append(f"  Tentativa {h['attempt']}: {h['error'] or h['result'][:80]}")
        return "\n".join(lines)


# Instância global
retry_policy = RetryPolicy()
