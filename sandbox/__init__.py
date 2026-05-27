"""sandbox — Módulo de execução isolada (Batch 7)."""
from sandbox.docker_runner import (
    run_python_sandboxed,
    run_shell_sandboxed,
    is_docker_available,
    is_firejail_available,
)
from sandbox.result_parser import parse_result
from sandbox.sandbox_config import get_profile, detect_profile

__all__ = [
    "run_python_sandboxed",
    "run_shell_sandboxed",
    "is_docker_available",
    "is_firejail_available",
    "parse_result",
    "get_profile",
    "detect_profile",
]
