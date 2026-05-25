"""
fix_telegram_loop.py
Corrige o conflito de event loop entre asyncio.run() e app.run_polling() no main.py
"""
from pathlib import Path

target = Path(r"C:\Users\Crypto Bull\Desktop\Agente Local\main.py")
content = target.read_text(encoding="utf-8")

# O problema: run_polling() tenta gerir o seu proprio loop mas ja ha um a correr
# Fix: usar app.initialize() + app.start() + updater.start_polling() de forma async

old = """        if app:
            logger.info("[Telegram] Bot a correr...")
            # O run_polling e bloqueante, corre na main thread
            app.run_polling()
        else:"""

new = """        if app:
            logger.info("[Telegram] Bot a correr...")
            # Iniciar o bot de forma async (compativel com event loop ja existente)
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            logger.info("[Telegram] Bot online. A aguardar mensagens...")
            # Manter vivo
            while True:
                await asyncio.sleep(1)
        else:"""

if old in content:
    content = content.replace(old, new)
    target.write_text(content, encoding="utf-8")
    print("OK - main.py corrigido!")
    print("Reinicia com: python main.py")
else:
    # Tentar versao alternativa (pode ter ligeiras diferencas de espacamento)
    import re
    pattern = r"app\.run_polling\(\)"
    if re.search(pattern, content):
        new_polling = (
            "await app.initialize()\n"
            "            await app.start()\n"
            "            await app.updater.start_polling()\n"
            "            logger.info('[Telegram] Bot online.')\n"
            "            while True:\n"
            "                await asyncio.sleep(1)"
        )
        content = re.sub(pattern, new_polling, content)
        target.write_text(content, encoding="utf-8")
        print("OK - main.py corrigido (via regex)!")
        print("Reinicia com: python main.py")
    else:
        print("AVISO: padrao nao encontrado no main.py")
        print("Mostra as linhas com 'run_polling':")
        for i, line in enumerate(content.splitlines(), 1):
            if "run_polling" in line or "Bot a correr" in line:
                print(f"  linha {i}: {repr(line)}")