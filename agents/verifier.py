"""
agents/verifier.py — Verificador de resultados de tool calls.

Verifica heuristicamente se o resultado de uma ferramenta faz sentido,
SEM chamar a API. Zero custo extra.

Filosofia:
  - Erros óbvios detetados localmente (regex + heurísticas)
  - Resultados suspeitos marcados para retry
  - Só falha se houver evidência clara de problema
"""
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─── Padrões de erro por ferramenta ──────────────────────────────────────────

# Prefixos universais de erro
ERROR_PREFIXES = (
    "erro", "error", "exception", "traceback", "fatal",
    "falhou", "failed", "not found", "não encontrado",
    "permission denied", "access denied", "no such file",
    "syntaxerror", "nameerror", "typeerror", "valueerror",
    "importerror", "modulenotfounderror", "attributeerror",
)

# Padrões que indicam sucesso garantido
SUCCESS_PATTERNS = {
    "write_file":       [r"escrito", r"guardado", r"saved", r"written", r"ok", r"sucesso"],
    "git_commit_push":  [r"pushed", r"main", r"origin", r"commit", r"\[main"],
    "run_python":       [],   # qualquer output sem traceback = ok
    "run_shell":        [],   # qualquer returncode=0 = ok
    "read_file":        [],   # qualquer conteúdo não-vazio = ok
    "list_files":       [],   # qualquer listagem = ok
    "web_search":       [r"http", r"www\.", r"resultado", r"result"],
}

# Padrões que indicam falha específica por ferramenta
FAILURE_PATTERNS = {
    "write_file":      [r"permission denied", r"is a directory", r"read.only"],
    "git_commit_push": [r"rejected", r"authentication", r"403", r"denied", r"conflict"],
    "run_python":      [r"Traceback", r"SyntaxError", r"NameError", r"ImportError",
                        r"TypeError", r"ValueError", r"AttributeError", r"IndentationError"],
    "run_shell":       [r"não é reconhecido", r"not recognized", r"not found",
                        r"access is denied", r"returncode: [^0]"],
    "read_file":       [r"no such file", r"não existe", r"not found", r"permission"],
    "create_agent":    [r"já existe", r"already exists", r"duplicado"],
}


class ToolResultVerifier:
    """
    Verifica se o resultado de uma tool call é válido.
    Usa apenas heurísticas locais — zero chamadas API.
    """

    def verify(self, tool_name: str, args: dict, result: Any) -> dict:
        """
        Verifica o resultado de uma ferramenta.

        Returns:
            {
                "ok": bool,
                "confidence": float,   # 0.0 a 1.0
                "reason": str,         # motivo se não ok
                "recoverable": bool,   # vale a pena retry?
            }
        """
        result_str = str(result).strip()
        result_lower = result_str.lower()

        # 1. Resultado vazio é suspeito
        if not result_str or result_str in ("None", "null", ""):
            return self._fail("Resultado vazio", recoverable=True)

        # 2. Verificar prefixos de erro universais
        for prefix in ERROR_PREFIXES:
            if result_lower.startswith(prefix):
                recoverable = self._is_recoverable(tool_name, result_lower)
                return self._fail(
                    f"Resultado começa com indicador de erro: '{prefix}'",
                    recoverable=recoverable,
                )

        # 3. Verificar padrões de falha específicos por ferramenta
        fail_patterns = FAILURE_PATTERNS.get(tool_name, [])
        for pattern in fail_patterns:
            if re.search(pattern, result_str, re.IGNORECASE):
                recoverable = self._is_recoverable(tool_name, result_lower)
                return self._fail(
                    f"Padrão de falha detetado em '{tool_name}': '{pattern}'",
                    recoverable=recoverable,
                )

        # 4. Para write_file: verificar que o path nos args não é suspeito
        if tool_name == "write_file":
            path = str(args.get("path", ""))
            content = str(args.get("content", ""))
            if not path:
                return self._fail("write_file sem 'path'", recoverable=False)
            if not content:
                return self._fail("write_file com conteúdo vazio", recoverable=False)

        # 5. Para run_python com Traceback no meio do output
        if tool_name == "run_python" and "Traceback" in result_str:
            return self._fail("Python lançou excepção", recoverable=True)

        # 6. run_shell com returncode não-zero
        if tool_name == "run_shell":
            match = re.search(r"[Rr]eturncode:\s*(-?\d+)", result_str)
            if match and match.group(1) != "0":
                return self._fail(
                    f"Shell retornou código {match.group(1)}",
                    recoverable=True,
                )

        # 7. git_commit_push — verificar que mencionou push/commit
        if tool_name == "git_commit_push":
            if not any(kw in result_lower for kw in ("pushed", "commit", "main", "origin", "branch")):
                return self._fail("git push não confirmado no output", recoverable=True)

        # Passou tudo — OK
        return {
            "ok":          True,
            "confidence":  0.9,
            "reason":      "",
            "recoverable": False,
        }

    def _fail(self, reason: str, recoverable: bool = True) -> dict:
        logger.debug(f"[Verifier] Falhou: {reason} (recuperável={recoverable})")
        return {
            "ok":          False,
            "confidence":  0.1,
            "reason":      reason,
            "recoverable": recoverable,
        }

    def _is_recoverable(self, tool_name: str, result_lower: str) -> bool:
        """Decide se vale a pena fazer retry desta falha."""
        # Erros de autenticação/permissão → não recuperável por retry simples
        non_recoverable_keywords = (
            "permission denied", "access denied", "authentication",
            "403", "401", "not found", "no such file",
        )
        for kw in non_recoverable_keywords:
            if kw in result_lower:
                return False
        return True


# Instância global reutilizável
verifier = ToolResultVerifier()
