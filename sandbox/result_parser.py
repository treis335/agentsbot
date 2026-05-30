"""
sandbox/result_parser.py — Parse de outputs de containers (stdout/stderr/returncode).

Normaliza o resultado do sandbox para o formato esperado pelos agentes.
"""

import re
from typing import Optional


def parse_result(sandbox_output: dict) -> str:
    """
    Converte output do sandbox para string formatada para o agente.

    Args:
        sandbox_output: Dict retornado por docker_runner.run_*_sandboxed()

    Returns:
        String formatada com resultado, erros e metadados de sandbox
    """
    success = sandbox_output.get("success", False)
    stdout = sandbox_output.get("stdout", "").strip()
    stderr = sandbox_output.get("stderr", "").strip()
    returncode = sandbox_output.get("returncode", -1)
    sandbox_type = sandbox_output.get("sandbox_type", "unknown")
    profile = sandbox_output.get("profile", "unknown")
    duration = sandbox_output.get("duration_s", 0)

    lines = []

    # Header de sandbox
    icon = "[OK]" if success else "[X]"
    lines.append(f"{icon} [Sandbox:{sandbox_type}/{profile}] rc={returncode} ({duration}s)")

    if stdout:
        lines.append(f"STDOUT:\n{stdout}")

    if stderr:
        # Filtrar warnings irrelevantes do Docker/firejail
        clean_stderr = _clean_stderr(stderr)
        if clean_stderr:
            lines.append(f"STDERR:\n{clean_stderr}")

    if not success and not stdout and not stderr:
        lines.append("Sem output — processo terminou sem produzir saída")

    return "\n".join(lines)


def _clean_stderr(stderr: str) -> str:
    """Remove mensagens de stderr irrelevantes do runtime."""
    noise_patterns = [
        r"^\s*$",
        r"firejail.*warning",
        r"docker.*warning",
        r"UserWarning:.*site-packages",
        r"DeprecationWarning",
        r"^\s*\^+\s*$",  # Linhas só com ^
    ]
    lines = []
    for line in stderr.splitlines():
        is_noise = any(re.search(p, line, re.IGNORECASE) for p in noise_patterns)
        if not is_noise:
            lines.append(line)
    return "\n".join(lines).strip()


def is_sandboxed_result(result_str: str) -> bool:
    """Verifica se um resultado já passou pelo sandbox."""
    return "[Sandbox:" in result_str


def extract_returncode(result_str: str) -> Optional[int]:
    """Extrai returncode de um resultado formatado."""
    m = re.search(r"rc=(-?\d+)", result_str)
    return int(m.group(1)) if m else None


def format_sandbox_summary(results: list[dict]) -> str:
    """
    Formata resumo de múltiplas execuções em sandbox.
    Útil para relatórios de testes.
    """
    if not results:
        return "Nenhuma execução em sandbox"

    total = len(results)
    success = sum(1 for r in results if r.get("success"))
    avg_duration = sum(r.get("duration_s", 0) for r in results) / total

    lines = [
        f"[DADOS] Sandbox Summary: {success}/{total} OK | avg {avg_duration:.1f}s",
    ]

    sandbox_types = set(r.get("sandbox_type", "?") for r in results)
    lines.append(f"   Modo: {', '.join(sandbox_types)}")

    failed = [r for r in results if not r.get("success")]
    if failed:
        lines.append(f"   [X] {len(failed)} falhas:")
        for f in failed[:3]:
            err = f.get("stderr", "")[:80]
            lines.append(f"      rc={f.get('returncode')} | {err}")

    return "\n".join(lines)
