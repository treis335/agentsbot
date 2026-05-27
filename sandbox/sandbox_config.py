"""
sandbox/sandbox_config.py — Limites de CPU, memória e filesystem por tipo de tarefa.

Centraliza todas as configurações de sandboxing.
Lido por docker_runner.py e fs_tools.py.
"""

from dataclasses import dataclass, field
from typing import Optional
from core.config import Config


@dataclass
class SandboxProfile:
    """Perfil de limites para um tipo de tarefa."""
    name: str
    cpu_period: int = 100_000       # Docker: período em microsegundos
    cpu_quota: int = 50_000         # Docker: quota (50k/100k = 50% de 1 CPU)
    memory_mb: int = 256            # Memória RAM máxima
    timeout_seconds: int = 30       # Timeout de execução
    network: bool = False           # Acesso a rede
    read_only_root: bool = True     # Filesystem root read-only
    allowed_paths: list = field(default_factory=list)  # Paths montados (read-only)
    writable_paths: list = field(default_factory=list)  # Paths com escrita


# Perfis predefinidos por tipo de tarefa
PROFILES: dict[str, SandboxProfile] = {

    # Scripts Python simples — sem rede, sem escrita
    "python_script": SandboxProfile(
        name="python_script",
        cpu_quota=25_000,      # 25% CPU
        memory_mb=128,
        timeout_seconds=30,
        network=False,
        read_only_root=True,
    ),

    # Testes (pytest) — precisam de ler o projecto
    "testing": SandboxProfile(
        name="testing",
        cpu_quota=50_000,      # 50% CPU
        memory_mb=256,
        timeout_seconds=120,
        network=False,
        read_only_root=True,
        allowed_paths=[str(Config.REPO_LOCAL_PATH)],
    ),

    # Shell genérico — mais permissivo mas ainda contido
    "shell": SandboxProfile(
        name="shell",
        cpu_quota=50_000,
        memory_mb=256,
        timeout_seconds=60,
        network=False,
        read_only_root=False,
        writable_paths=[str(Config.REPO_LOCAL_PATH)],
    ),

    # Builds (pip install, npm, etc.) — precisam de rede e mais memória
    "build": SandboxProfile(
        name="build",
        cpu_quota=80_000,      # 80% CPU
        memory_mb=512,
        timeout_seconds=300,
        network=True,
        read_only_root=False,
        writable_paths=[str(Config.REPO_LOCAL_PATH)],
    ),

    # Análise de dados — mais memória, sem rede
    "data_analysis": SandboxProfile(
        name="data_analysis",
        cpu_quota=80_000,
        memory_mb=1024,
        timeout_seconds=180,
        network=False,
        read_only_root=True,
        allowed_paths=[str(Config.REPO_LOCAL_PATH)],
    ),
}


def get_profile(task_type: str) -> SandboxProfile:
    """Retorna perfil para o tipo de tarefa, com fallback para 'python_script'."""
    return PROFILES.get(task_type, PROFILES["python_script"])


def detect_profile(code_or_command: str) -> str:
    """
    Detecta automaticamente o perfil adequado pelo conteúdo.
    """
    text = code_or_command.lower()

    if any(x in text for x in ["pip install", "npm install", "apt-get", "curl", "wget"]):
        return "build"
    if any(x in text for x in ["pytest", "unittest", "test_", "_test.py"]):
        return "testing"
    if any(x in text for x in ["pandas", "numpy", "matplotlib", "scipy", "sklearn"]):
        return "data_analysis"
    if any(x in text for x in ["import ", "def ", "class ", "print("]):
        return "python_script"
    return "shell"
