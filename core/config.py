"""
core/config.py — Configuracao centralizada do ecossistema.

Carrega de .env com fallback, valida tipos, e expoe tudo
como atributos de classe para acesso rapido.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Carregar .env da raiz do projeto
BASE_DIR = Path(__file__).parent.parent.resolve()
load_dotenv(BASE_DIR / ".env")


class Config:
    """Configuracao centralizada e validada."""

    # --- DeepSeek ---
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    OWNER_TELEGRAM_ID: int = int(os.getenv("OWNER_TELEGRAM_ID", "0"))

    # --- GitHub ---
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "treis335/agentsbot")

    # --- Caminhos ---
    REPO_LOCAL_PATH: Path = Path(os.getenv("REPO_LOCAL_PATH", str(BASE_DIR)))
    MEMORY_DIR: Path = BASE_DIR / "memory"
    AGENTS_DIR: Path = BASE_DIR / "agents"
    TOOLS_DIR: Path = BASE_DIR / "tools"
    TASKS_DIR: Path = BASE_DIR / "tasks"
    DASHBOARD_DIR: Path = BASE_DIR / "dashboard"
    SECURITY_DIR: Path = BASE_DIR / "security"
    MONITORING_DIR: Path = BASE_DIR / "monitoring"
    PIPELINES_DIR: Path = BASE_DIR / "pipelines"
    API_DIR: Path = BASE_DIR / "api"
    DATA_DIR: Path = BASE_DIR / "data"

    # --- Ficheiros ---
    AGENTS_FILE: Path = BASE_DIR / "agents" / "registry" / "agents.json"
    MASTER_MEMORY_FILE: Path = MEMORY_DIR / "master_context.json"
    TASKS_FILE: Path = TASKS_DIR / "queue" / "tasks.json"
    AUDIT_LOG: Path = SECURITY_DIR / "audit" / "audit.log"

    # --- Sistema ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    AGENT_INTERVAL: int = int(os.getenv("AGENT_INTERVAL", "300"))
    MAX_TOOL_ITERATIONS: int = 30
    MAX_TOOL_RETRIES: int = 2

    # --- Validacao ---
    @classmethod
    def validate(cls) -> list[str]:
        """Valida configuracao e retorna lista de avisos."""
        warnings = []
        if not cls.DEEPSEEK_API_KEY or "placeholder" in cls.DEEPSEEK_API_KEY:
            warnings.append("DEEPSEEK_API_KEY nao configurada")
        if not cls.TELEGRAM_BOT_TOKEN or "placeholder" in cls.TELEGRAM_BOT_TOKEN:
            warnings.append("TELEGRAM_BOT_TOKEN nao configurado")
        if cls.OWNER_TELEGRAM_ID == 0:
            warnings.append("OWNER_TELEGRAM_ID nao configurado")
        return warnings

    @classmethod
    def to_dict(cls) -> dict:
        """Exporta config como dict (sem segredos)."""
        return {
            "deepseek_base_url": cls.DEEPSEEK_BASE_URL,
            "github_repo": cls.GITHUB_REPO,
            "repo_path": str(cls.REPO_LOCAL_PATH),
            "log_level": cls.LOG_LEVEL,
            "agent_interval": cls.AGENT_INTERVAL,
            "max_tool_iterations": cls.MAX_TOOL_ITERATIONS,
        }
