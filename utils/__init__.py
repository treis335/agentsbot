"""
utils — Utilitários do ecossistema Correoto
"""
import sys
import os
import logging

def force_utf8():
    """Força UTF-8 no stdout/stderr para evitar UnicodeEncodeError no Windows."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.environ["PYTHONIOENCODING"] = "utf-8:replace"


class TelegramLogFilter(logging.Filter):
    """Filtra logs de erro do Telegram HTTP 409 Conflict para evitar spam."""
    
    def filter(self, record):
        msg = record.getMessage()
        # Filtrar 409 Conflict do Telegram (múltiplas instâncias)
        if "409 Conflict" in msg and "telegram" in msg.lower():
            return False
        # Filtrar polling exceptions do Telegram
        if "Exception happened while polling" in msg:
            return False
        # Filtrar "No error handlers are registered"
        if "No error handlers are registered" in msg:
            return False
        return True


def suppress_telegram_errors():
    """Adiciona filtro para suprimir logs de erro do Telegram."""
    for handler in logging.root.handlers:
        handler.addFilter(TelegramLogFilter())
    
    # Também filtrar loggers específicos do Telegram
    for name in ['telegram', 'telegram.ext.Updater', 'telegram.ext.Application', 'httpx']:
        logger = logging.getLogger(name)
        logger.addFilter(TelegramLogFilter())
        logger.setLevel(logging.WARNING)  # Só mostrar WARNING+ do Telegram


def setup_logging(level=logging.INFO, suppress_telegram=True):
    """Configura logging do ecossistema com opção de suprimir Telegram."""
    force_utf8()
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('main.log', encoding='utf-8'),
        ]
    )
    
    if suppress_telegram:
        suppress_telegram_errors()
    
    return logging.getLogger(__name__)
