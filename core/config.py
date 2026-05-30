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

    # --- DeepSeek (LLM principal) ---
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # --- LLM Agent settings ---
    LLM_MAX_TOOL_ITERATIONS: int = int(os.getenv("LLM_MAX_TOOL_ITERATIONS", "5"))
    LLM_MAX_HISTORY: int = int(os.getenv("LLM_MAX_HISTORY", "30"))

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

    # --- Batch 6: Local Inference (Ollama) ---
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    LOCAL_MODEL: str = os.getenv("LOCAL_MODEL", "qwen2.5-coder:7b")
    ROUTING_THRESHOLD: float = float(os.getenv("ROUTING_THRESHOLD", "0.4"))
    # 0.0 = sempre DeepSeek | 1.0 = sempre Ollama | 0.4 = recomendado
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # --- Batch 7: Sandbox Execution ---
    SANDBOX_ENABLED: bool = os.getenv("SANDBOX_ENABLED", "false").lower() == "true"
    SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "30"))
    SANDBOX_MEMORY_MB: int = int(os.getenv("SANDBOX_MEMORY_MB", "256"))
    # SANDBOX_ENABLED=true  → usa Docker/firejail quando disponível
    # SANDBOX_ENABLED=false → usa subprocess restrito (fallback seguro)

    # --- Batch 9: Self-Improvement Loop ---
    SELF_IMPROVE_ENABLED: bool = os.getenv("SELF_IMPROVE_ENABLED", "true").lower() == "true"
    SELF_IMPROVE_EVERY_N_CYCLES: int = int(os.getenv("SELF_IMPROVE_EVERY_N_CYCLES", "10"))
    SELF_IMPROVE_MAX_PATCHES: int = int(os.getenv("SELF_IMPROVE_MAX_PATCHES", "3"))

    # --- Notificações Proactivas ---
    NOTIFY_ON_TASK_COMPLETE: str = os.getenv("NOTIFY_ON_TASK_COMPLETE", "true")
    NOTIFY_ON_TASK_FAIL: str = os.getenv("NOTIFY_ON_TASK_FAIL", "true")
    NOTIFY_ON_SELF_IMPROVE: str = os.getenv("NOTIFY_ON_SELF_IMPROVE", "true")
    NOTIFY_DAILY_SUMMARY: str = os.getenv("NOTIFY_DAILY_SUMMARY", "true")
    NOTIFY_DAILY_SUMMARY_HOUR: int = int(os.getenv("NOTIFY_DAILY_SUMMARY_HOUR", "8"))

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
