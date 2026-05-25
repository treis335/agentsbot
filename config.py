import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OWNER_TELEGRAM_ID  = int(os.getenv("OWNER_TELEGRAM_ID", "0"))

MEMORY_DIR         = os.getenv("MEMORY_DIR", "memory")
MASTER_MEMORY_FILE = os.path.join(MEMORY_DIR, "master_context.json")

LOG_LEVEL          = os.getenv("LOG_LEVEL", "INFO")
AGENT_INTERVAL     = int(os.getenv("AGENT_INTERVAL", "300"))

REPO_LOCAL_PATH    = os.getenv("REPO_LOCAL_PATH", "C:/Users/Crypto Bull/Desktop/Agente Local")