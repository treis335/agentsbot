"""
tools/web_tools.py — Ferramentas para criar e gerir sites.

Permite aos agentes criar sites completos (HTML/CSS/JS),
estruturar projectos web, e fazer deploy via GitHub Pages.
"""
import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def create_website(
    name: str,
    description: str,
    pages: list = None,
    style: str = "modern",
) -> str:
    """
    Cria a estrutura completa de um site estático.

    Args:
        name:        Nome do site (usado como título e pasta)
        description: Descrição / propósito do site
        pages:       Lista de páginas a criar (default: ["index"])
        style:       Estilo visual ("modern", "minimal", "dark")

    Returns:
        Caminho da pasta criada + instruções de deploy
    """
    from core.config import Config
    repo_dir = Path(Config.REPO_LOCAL_PATH)

    pages = pages or ["index"]
    slug = name.lower().replace(" ", "-").replace("_", "-")
    site_dir = repo_dir / "sites" / slug
    site_dir.mkdir(parents=True, exist_ok=True)

    # CSS base por estilo
    styles = {
        "modern": """
:root { --bg: #ffffff; --text: #1a1a2e; --accent: #4f46e5; --muted: #6b7280; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }
header { background:var(--accent); color:white; padding:16px 32px; display:flex; align-items:center; justify-content:space-between; }
header h1 { font-size:22px; font-weight:700; }
nav a { color:white; text-decoration:none; margin-left:24px; font-size:14px; opacity:.85; }
nav a:hover { opacity:1; }
.hero { padding:80px 32px; text-align:center; background:linear-gradient(135deg,#f8fafc,#e8eaf6); }
.hero h2 { font-size:42px; font-weight:800; margin-bottom:16px; color:var(--accent); }
.hero p { font-size:18px; color:var(--muted); max-width:600px; margin:0 auto 32px; }
.btn { background:var(--accent); color:white; padding:14px 32px; border-radius:8px; text-decoration:none; font-weight:600; display:inline-block; }
.btn:hover { background:#4338ca; }
.section { padding:60px 32px; max-width:1100px; margin:0 auto; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:24px; margin-top:32px; }
.card { background:white; border:1px solid #e5e7eb; border-radius:12px; padding:24px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.card h3 { font-size:18px; margin-bottom:8px; color:var(--accent); }
footer { background:#1a1a2e; color:#9ca3af; padding:32px; text-align:center; font-size:14px; margin-top:60px; }
""",
        "minimal": """
:root { --bg: #fafafa; --text: #222; --accent: #000; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: Georgia, serif; background:var(--bg); color:var(--text); line-height:1.8; max-width:720px; margin:0 auto; padding:40px 20px; }
header { border-bottom:2px solid #000; padding-bottom:20px; margin-bottom:40px; }
header h1 { font-size:28px; }
nav a { color:#000; margin-right:20px; }
h2 { font-size:28px; margin:40px 0 16px; }
p { margin-bottom:16px; color:#444; }
.btn { background:#000; color:#fff; padding:10px 24px; text-decoration:none; }
footer { margin-top:60px; padding-top:20px; border-top:1px solid #ddd; font-size:13px; color:#888; }
""",
        "dark": """
:root { --bg: #0d1117; --text: #c9d1d9; --accent: #58a6ff; --surface: #161b22; --border: #21262d; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }
header { background:var(--surface); border-bottom:1px solid var(--border); padding:16px 32px; display:flex; align-items:center; justify-content:space-between; }
header h1 { font-size:20px; color:var(--accent); }
nav a { color:var(--text); text-decoration:none; margin-left:24px; font-size:14px; }
nav a:hover { color:var(--accent); }
.hero { padding:80px 32px; text-align:center; }
.hero h2 { font-size:40px; font-weight:700; color:var(--accent); margin-bottom:16px; }
.hero p { color:#8b949e; max-width:600px; margin:0 auto 32px; font-size:17px; }
.btn { background:var(--accent); color:#0d1117; padding:12px 28px; border-radius:6px; text-decoration:none; font-weight:600; display:inline-block; }
.section { padding:60px 32px; max-width:1100px; margin:0 auto; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:20px; margin-top:32px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:24px; }
.card h3 { color:var(--accent); margin-bottom:8px; }
footer { background:var(--surface); border-top:1px solid var(--border); padding:24px 32px; text-align:center; font-size:13px; color:#8b949e; margin-top:60px; }
""",
    }

    css_content = styles.get(style, styles["modern"])

    # Criar style.css
    (site_dir / "style.css").write_text(css_content, encoding="utf-8")

    # Criar cada página
    created = []
    for page in pages:
        is_home = page in ("index", "home", "início")
        page_title = name if is_home else page.replace("-", " ").title()
        nav_links = "\n".join(
            f'<a href="{p if p != "index" else "index"}.html">{p.title()}</a>'
            for p in pages
        )

        if is_home:
            body_content = f"""
    <div class="hero">
        <h2>{name}</h2>
        <p>{description}</p>
        <a href="#sobre" class="btn">Saber mais</a>
    </div>
    <div class="section" id="sobre">
        <h2>Sobre</h2>
        <p>{description}</p>
        <div class="grid">
            <div class="card"><h3>[ESTRELA] Moderno</h3><p>Design limpo e profissional.</p></div>
            <div class="card"><h3>[START] Rápido</h3><p>Optimizado para performance.</p></div>
            <div class="card"><h3>📱 Responsivo</h3><p>Funciona em todos os dispositivos.</p></div>
        </div>
    </div>"""
        else:
            body_content = f"""
    <div class="section">
        <h2>{page_title}</h2>
        <p>Conteúdo da página {page_title}. Edita este ficheiro para personalizar.</p>
    </div>"""

        html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title} — {name}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
    <h1>{name}</h1>
    <nav>{nav_links}</nav>
</header>
<main>{body_content}
</main>
<footer>
    <p>&copy; {name} — Criado por agentsbot</p>
</footer>
</body>
</html>"""

        filename = f"{'index' if is_home else page}.html"
        (site_dir / filename).write_text(html, encoding="utf-8")
        created.append(filename)

    # Criar README para o site
    readme = f"""# {name}

{description}

## Ficheiros
{chr(10).join(f'- `{f}`' for f in created)}
- `style.css` — estilos ({style})

## Deploy no GitHub Pages
1. Mover esta pasta para a raiz do repo ou usar como subpasta
2. Activar GitHub Pages em Settings > Pages
3. Seleccionar branch `main` e pasta `/docs` (ou mover site para `/docs`)

## Editar
- Abre qualquer `.html` num editor para personalizar o conteúdo
- Edita `style.css` para mudar cores e layout
"""
    (site_dir / "README.md").write_text(readme, encoding="utf-8")

    rel_path = site_dir.relative_to(repo_dir)
    result = (
        f"[OK] Site '{name}' criado em `{rel_path}/`\n"
        f"Ficheiros: {', '.join(created + ['style.css', 'README.md'])}\n"
        f"Estilo: {style}\n"
        f"Para publicar: git commit + push, depois activar GitHub Pages."
    )
    logger.info(f"[create_website] {result}")
    return result


async def add_page(site_name: str, page_name: str, content: str = "") -> str:
    """Adiciona uma nova página a um site existente."""
    from core.config import Config
    repo_dir = Path(Config.REPO_LOCAL_PATH)
    slug = site_name.lower().replace(" ", "-")
    site_dir = repo_dir / "sites" / slug

    if not site_dir.exists():
        return f"Site '{site_name}' não encontrado em sites/{slug}/"

    filename = f"{page_name.lower().replace(' ', '-')}.html"
    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_name.title()} — {site_name}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="section">
    <h2>{page_name.title()}</h2>
    {content or '<p>Conteúdo desta página.</p>'}
</div>
</body>
</html>"""
    (site_dir / filename).write_text(html, encoding="utf-8")
    return f"[OK] Página `{filename}` adicionada a `sites/{slug}/`"


# ── Schemas para o executor ───────────────────────────────────────────────────

WEBSITE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_website",
            "description": (
                "Cria um site completo (HTML/CSS) com múltiplas páginas. "
                "Usa para criar landing pages, portfolios, sites de produto, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name":        {"type": "string", "description": "Nome do site"},
                    "description": {"type": "string", "description": "O que o site faz / propósito"},
                    "pages":       {"type": "array", "items": {"type": "string"},
                                   "description": "Páginas a criar, ex: ['index', 'sobre', 'contacto']"},
                    "style":       {"type": "string", "enum": ["modern", "minimal", "dark"],
                                   "description": "Estilo visual"},
                },
                "required": ["name", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_page",
            "description": "Adiciona uma nova página HTML a um site existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_name":  {"type": "string"},
                    "page_name":  {"type": "string"},
                    "content":    {"type": "string", "description": "HTML do conteúdo (opcional)"},
                },
                "required": ["site_name", "page_name"],
            },
        },
    },
]
