"""
core/safe_print.py — Print SEGURO para Windows (cp1252).

Substitui emojis por equivalentes ASCII para evitar:
    UnicodeEncodeError: 'charmap' codec can't encode character

Uso:
    from core.safe_print import sp
    sp("[FIX] Tools a usar REPO_DIR: {path}")  # → "[Tools] Tools a usar REPO_DIR: ..."
"""
import sys
import logging

# ─── Mapa de substituição de emojis → texto ASCII ─────────────────────────
EMOJI_MAP = {
    # Ação / Estado
    "[OK]": "[OK]",
    "[X]": "[ERRO]",
    "[!]": "[AVISO]",
    "[LOOP]": "[REINICIAR]",
    "[START]": "[INICIAR]",
    "[PARAR]": "[PARAR]",
    "[FIX]": "[REPARAR]",
    "[FATAL]": "[FATAL]",
    "[TCHAU]": "[FIM]",
    "[BUSCA]": "[PROCURAR]",
    "[LISTA]": "[LISTA]",
    "[PIN]": "[FIXAR]",
    "[PASTA]": "[PASTA]",
    "[DADOS]": "[DADOS]",
    "[SOBE]": "[CRESCER]",
    "[LIVRO]": "[LIVROS]",
    "[DOC]": "[DOC]",
    "[EDIT]": "[EDITAR]",
    "[SINAL]": "[SINAL]",
    "[PACOTE]": "[PACOTE]",
    "[VAZIO]": "[VAZIO]",

    # Tecnologia / IA
    "[IA]": "[IA]",
    "[MENTE]": "[MENTE]",
    "[DNA]": "[ADN]",
    "[IDEA]": "[IDEIA]",
    "[PC]": "[PC]",
    "[RAPIDO]": "[RAPIDO]",
    "[CIENCIA]": "[CIENCIA]",
    "[LINK]": "[LINK]",
    "[WEB]": "[WEB]",
    "[CHAT]": "[CHAT]",
    "[PENSAR]": "[PENSAR]",

    # Interface / UI
    "[VERDE]": "[VERDE]",
    "[VERM]": "[VERMELHO]",
    "[HORA]": "[TEMPO]",
    "[DIN]": "[DINHEIRO]",
    "[TROF]": "[TROFEU]",
    "[OURO]": "[OURO]",
    "[ALVO]": "[ALVO]",
    "[OBRA]": "[CONSTRUIR]",
    "[OBS]": "[OBSERVAR]",
    "[MUNDO]": "[MUNDO]",
    "[MAO]": ["[APERTAR_MAO]"],
    "[GRUPO]": "[GRUPO]",
    "[CORT]": "[CORTAR]",
    "[COMP]": "[COMPRIMIR]",
    "[LIMPA]": "[LIMPAR]",
    "[ESTRELA]": "[ESTRELA]",
    "[DORMIR]": "[DORMIR]",
    "[EXPL]": "[EXPLOSAO]",
    "[FOGO]": "[FOGO]",
    "[HOSP]": "[HOSPITAL]",
    "[ALARME]": "[ALARME]",
    "[SALVAR]": "[SALVAR]",
    "[ENG]": "[ENGRENAGEM]",

    # Outros
    "[OK]": "[OK]",
    "[ERR]": "[ERR]",
    "[?]": "[?]",
    "[ESTRELA]": "[ESTRELA]",
}


def safe_text(text: str) -> str:
    """Substitui todos os emojis por texto ASCII seguro."""
    for emoji, replacement in EMOJI_MAP.items():
        if isinstance(replacement, list):
            replacement = replacement[0]
        text = text.replace(emoji, replacement)
    return text


def sp(*args, sep=" ", end="\n", flush=False, file=None):
    """
    safe_print — imprime sem emojis, seguro para Windows cp1252.
    Uso idêntico ao print() normal.
    """
    text = sep.join(str(a) for a in args)
    text = safe_text(text)
    if file is None:
        file = sys.stdout
    print(text, end=end, flush=flush, file=file)


def configure_root_logger(level=logging.INFO):
    """
    Configura o logging root para usar um handler que filtra emojis.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    class EmojiSafeFormatter(logging.Formatter):
        def format(self, record):
            msg = super().format(record)
            return safe_text(msg)

    formatter = EmojiSafeFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Remove handlers existentes para evitar duplicação
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)

    return root


# ─── Atalho ────────────────────────────────────────────────────────────────
safe_print = sp
