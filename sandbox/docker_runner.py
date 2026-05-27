"""
sandbox/docker_runner.py — Executa código em container Docker isolado.

Quando Docker não está disponível, usa fallback com subprocess restrito.
Zero custo API — isolamento local.
"""

import asyncio
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from sandbox.sandbox_config import SandboxProfile, get_profile, detect_profile

logger = logging.getLogger(__name__)

# Imagem base para o sandbox
SANDBOX_IMAGE = "sandbox-agentsbot:latest"
DOCKERFILE_PATH = Path(__file__).parent / "Dockerfile.sandbox"


def is_docker_available() -> bool:
    """Verifica se Docker está disponível no sistema."""
    return shutil.which("docker") is not None


def is_firejail_available() -> bool:
    """Verifica se firejail está disponível (sandboxing leve sem Docker)."""
    return shutil.which("firejail") is not None


async def run_python_sandboxed(
    code: str,
    task_type: str = "auto",
    timeout: Optional[int] = None,
) -> dict:
    """
    Executa código Python em sandbox isolado.

    Estratégia de isolamento (por ordem de preferência):
    1. Docker (melhor isolamento)
    2. Firejail (sem Docker)
    3. Subprocess restrito com timeout (fallback sempre disponível)

    Returns:
        {success, stdout, stderr, returncode, sandbox_type, duration_s}
    """
    profile_name = task_type if task_type != "auto" else detect_profile(code)
    profile = get_profile(profile_name)
    actual_timeout = timeout or profile.timeout_seconds

    if is_docker_available():
        return await _run_docker(code, profile, actual_timeout, lang="python")
    elif is_firejail_available():
        return await _run_firejail_python(code, profile, actual_timeout)
    else:
        logger.warning("[Sandbox] Docker e firejail indisponíveis — usando subprocess restrito")
        return await _run_restricted_subprocess_python(code, actual_timeout)


async def run_shell_sandboxed(
    command: str,
    task_type: str = "auto",
    timeout: Optional[int] = None,
) -> dict:
    """
    Executa comando shell em sandbox isolado.
    """
    profile_name = task_type if task_type != "auto" else detect_profile(command)
    profile = get_profile(profile_name)
    actual_timeout = timeout or profile.timeout_seconds

    if is_docker_available():
        return await _run_docker(command, profile, actual_timeout, lang="shell")
    elif is_firejail_available():
        return await _run_firejail_shell(command, profile, actual_timeout)
    else:
        logger.warning("[Sandbox] Docker e firejail indisponíveis — usando subprocess restrito")
        return await _run_restricted_subprocess_shell(command, actual_timeout)


# ──────────────────────────────────────────────
# Docker runner
# ──────────────────────────────────────────────

async def _run_docker(
    code_or_cmd: str,
    profile: SandboxProfile,
    timeout: int,
    lang: str = "python",
) -> dict:
    """Executa em container Docker isolado."""
    import time
    start = time.monotonic()

    # Garantir que a imagem existe
    await _ensure_image()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        if lang == "python":
            script_file = tmpdir_path / "script.py"
            script_file.write_text(code_or_cmd, encoding="utf-8")
            cmd_in_container = ["python3", "/sandbox/script.py"]
        else:
            script_file = tmpdir_path / "script.sh"
            script_file.write_text(f"#!/bin/bash\nset -e\n{code_or_cmd}", encoding="utf-8")
            script_file.chmod(0o755)
            cmd_in_container = ["bash", "/sandbox/script.sh"]

        # Construir comando docker run
        docker_cmd = [
            "docker", "run",
            "--rm",
            "--name", f"sandbox_{os.getpid()}_{id(code_or_cmd)}",
            # Limites de recursos
            f"--cpu-period={profile.cpu_period}",
            f"--cpu-quota={profile.cpu_quota}",
            f"--memory={profile.memory_mb}m",
            f"--memory-swap={profile.memory_mb}m",  # Sem swap
            # Segurança
            "--no-new-privileges",
            "--security-opt", "no-new-privileges:true",
        ]

        # Rede
        if not profile.network:
            docker_cmd += ["--network", "none"]

        # Filesystem read-only
        if profile.read_only_root:
            docker_cmd += ["--read-only"]
            docker_cmd += ["--tmpfs", "/tmp:size=50m"]

        # Montar script
        docker_cmd += ["-v", f"{tmpdir}:/sandbox:ro"]

        # Paths adicionais (read-only)
        for path in profile.allowed_paths:
            docker_cmd += ["-v", f"{path}:{path}:ro"]

        # Paths com escrita
        for path in profile.writable_paths:
            docker_cmd += ["-v", f"{path}:{path}:rw"]

        docker_cmd += [SANDBOX_IMAGE] + cmd_in_container

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            duration = round(time.monotonic() - start, 2)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode(errors="replace")[:4000],
                "stderr": stderr.decode(errors="replace")[:2000],
                "returncode": proc.returncode,
                "sandbox_type": "docker",
                "profile": profile.name,
                "duration_s": duration,
            }
        except asyncio.TimeoutError:
            # Matar container se ainda estiver a correr
            try:
                await asyncio.create_subprocess_exec(
                    "docker", "kill", f"sandbox_{os.getpid()}_{id(code_or_cmd)}",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except Exception:
                pass
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Timeout após {timeout}s",
                "returncode": -1,
                "sandbox_type": "docker",
                "profile": profile.name,
                "duration_s": timeout,
            }


async def _ensure_image():
    """Garante que a imagem sandbox existe. Constrói se necessário."""
    # Verificar se já existe
    proc = await asyncio.create_subprocess_exec(
        "docker", "image", "inspect", SANDBOX_IMAGE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    if proc.returncode == 0:
        return  # Imagem já existe

    # Construir imagem
    if not DOCKERFILE_PATH.exists():
        raise RuntimeError(f"Dockerfile não encontrado: {DOCKERFILE_PATH}")

    logger.info(f"[Sandbox] A construir imagem {SANDBOX_IMAGE}...")
    proc = await asyncio.create_subprocess_exec(
        "docker", "build", "-t", SANDBOX_IMAGE, "-f", str(DOCKERFILE_PATH),
        str(DOCKERFILE_PATH.parent),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao construir imagem: {stderr.decode()[:500]}")
    logger.info(f"[Sandbox] Imagem {SANDBOX_IMAGE} construída com sucesso")


# ──────────────────────────────────────────────
# Firejail runner (sem Docker)
# ──────────────────────────────────────────────

async def _run_firejail_python(code: str, profile: SandboxProfile, timeout: int) -> dict:
    """Executa Python com firejail como sandbox leve."""
    import time
    start = time.monotonic()

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        fname = f.name

    try:
        cmd = [
            "firejail",
            "--quiet",
            "--noprofile",
            "--net=none",          # Sem rede
            "--private-tmp",       # /tmp privado
            "--noroot",            # Sem root
            "--rlimit-as=" + str(profile.memory_mb * 1024 * 1024),
            sys.executable, fname,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        duration = round(time.monotonic() - start, 2)
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode(errors="replace")[:4000],
            "stderr": stderr.decode(errors="replace")[:2000],
            "returncode": proc.returncode,
            "sandbox_type": "firejail",
            "profile": profile.name,
            "duration_s": duration,
        }
    except asyncio.TimeoutError:
        return {"success": False, "stdout": "", "stderr": f"Timeout após {timeout}s",
                "returncode": -1, "sandbox_type": "firejail", "profile": profile.name, "duration_s": timeout}
    finally:
        Path(fname).unlink(missing_ok=True)


async def _run_firejail_shell(command: str, profile: SandboxProfile, timeout: int) -> dict:
    """Executa shell com firejail."""
    import time
    start = time.monotonic()

    cmd = ["firejail", "--quiet", "--noprofile", "--net=none",
           "--private-tmp", "--noroot", "bash", "-c", command]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        duration = round(time.monotonic() - start, 2)
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode(errors="replace")[:4000],
            "stderr": stderr.decode(errors="replace")[:2000],
            "returncode": proc.returncode,
            "sandbox_type": "firejail",
            "profile": profile.name,
            "duration_s": duration,
        }
    except asyncio.TimeoutError:
        return {"success": False, "stdout": "", "stderr": f"Timeout após {timeout}s",
                "returncode": -1, "sandbox_type": "firejail", "profile": profile.name, "duration_s": timeout}


# ──────────────────────────────────────────────
# Fallback: subprocess restrito
# ──────────────────────────────────────────────

async def _run_restricted_subprocess_python(code: str, timeout: int) -> dict:
    """
    Fallback sem Docker/firejail.
    Executa com timeout e no directório do repo (contido por cwd).
    """
    import time
    from core.config import Config

    start = time.monotonic()

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        fname = f.name

    try:
        # Ambiente mínimo — sem variáveis de ambiente sensíveis
        safe_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": str(Config.REPO_LOCAL_PATH),
            "HOME": str(Config.REPO_LOCAL_PATH),
        }
        proc = await asyncio.create_subprocess_exec(
            sys.executable, fname,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Config.REPO_LOCAL_PATH),
            env=safe_env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        duration = round(time.monotonic() - start, 2)
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode(errors="replace")[:4000],
            "stderr": stderr.decode(errors="replace")[:2000],
            "returncode": proc.returncode,
            "sandbox_type": "subprocess_restricted",
            "profile": "fallback",
            "duration_s": duration,
        }
    except asyncio.TimeoutError:
        return {"success": False, "stdout": "", "stderr": f"Timeout após {timeout}s",
                "returncode": -1, "sandbox_type": "subprocess_restricted", "profile": "fallback", "duration_s": timeout}
    finally:
        Path(fname).unlink(missing_ok=True)


async def _run_restricted_subprocess_shell(command: str, timeout: int) -> dict:
    """Fallback shell restrito."""
    import time
    from core.config import Config

    # Bloquear comandos perigosos mesmo no fallback
    BLOCKED = ["rm -rf /", "mkfs", "dd if=", "> /dev/", "chmod 777 /",
               ":(){ :|:& };:", "fork bomb", "shutdown", "reboot", "halt"]
    cmd_lower = command.lower()
    if any(b in cmd_lower for b in BLOCKED):
        return {"success": False, "stdout": "",
                "stderr": "Comando bloqueado por razões de segurança",
                "returncode": -1, "sandbox_type": "subprocess_restricted",
                "profile": "fallback", "duration_s": 0}

    start = time.monotonic()
    safe_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Config.REPO_LOCAL_PATH),
            env=safe_env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        duration = round(time.monotonic() - start, 2)
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode(errors="replace")[:4000],
            "stderr": stderr.decode(errors="replace")[:2000],
            "returncode": proc.returncode,
            "sandbox_type": "subprocess_restricted",
            "profile": "fallback",
            "duration_s": duration,
        }
    except asyncio.TimeoutError:
        return {"success": False, "stdout": "", "stderr": f"Timeout após {timeout}s",
                "returncode": -1, "sandbox_type": "subprocess_restricted",
                "profile": "fallback", "duration_s": timeout}
