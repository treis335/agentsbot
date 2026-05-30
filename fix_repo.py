"""
fix_repo.py - Correção automática do repositório agentsbot / NEXUS
Resolve:
  1. Pastas-sombra que bloqueiam imports Python
  2. Agentes duplicados em agents.json
  3. __pycache__ obsoletos
  4. Cria requirements.txt se não existir
"""

import os
import json
import shutil
import sys
import importlib.util
from pathlib import Path

# -- Cores para output no terminal --------------------------------------------
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}[OK]{RESET} {msg}")
def err(msg):  print(f"  {RED}[ERR]{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}[!]{RESET} {msg}")
def info(msg): print(f"  {BLUE}->{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")

# -- Detetar raiz do repositório -----------------------------------------------
def find_repo_root():
    """Procura a raiz do repo a partir do diretório atual ou do script."""
    candidates = [
        Path.cwd(),
        Path(__file__).parent,
    ]
    markers = ["agents.json", "nexus_core.py", "nexus.py"]
    for base in candidates:
        for p in [base] + list(base.parents)[:3]:
            if any((p / m).exists() for m in markers):
                return p
    return Path.cwd()


# -- PASSO 1: Remover pastas-sombra -------------------------------------------
def fix_shadow_folders(root: Path) -> int:
    """
    Remove pastas que têm o mesmo nome que ficheiros .py no mesmo diretório.
    Estas pastas com __init__.py vazio impedem que Python importe o ficheiro correto.
    """
    header("PASSO 1 — Pastas-sombra")
    removed = 0

    for py_file in root.rglob("*.py"):
        # Ignora o próprio script e ficheiros dentro de pastas de sistema
        if py_file.name == "fix_repo.py":
            continue
        if any(part.startswith(".") for part in py_file.parts):
            continue

        shadow_dir = py_file.parent / py_file.stem

        if shadow_dir.is_dir():
            # Verifica que é mesmo uma pasta-sombra:
            # deve conter apenas __init__.py (vazio ou quase) e __pycache__
            files_in_dir = [
                f for f in shadow_dir.iterdir()
                if f.name != "__pycache__" and not f.name.startswith(".")
            ]
            is_shadow = (
                len(files_in_dir) == 0
                or (
                    len(files_in_dir) == 1
                    and files_in_dir[0].name == "__init__.py"
                    and files_in_dir[0].stat().st_size < 50
                )
            )

            if is_shadow:
                try:
                    shutil.rmtree(shadow_dir)
                    ok(f"Removida pasta-sombra: {shadow_dir.relative_to(root)}/")
                    removed += 1
                except Exception as e:
                    err(f"N?o foi poss?vel remover {shadow_dir.name}/: {e}")
            else:
                warn(f"Pasta {shadow_dir.relative_to(root)}/ tem conte?do ? ignorada (verifica manualmente)")

    if removed == 0:
        ok("Nenhuma pasta-sombra encontrada")
    else:
        info(f"{removed} pasta(s)-sombra removida(s)")

    return removed


# -- PASSO 2: Limpar __pycache__ -----------------------------------------------
def clean_pycache(root: Path) -> int:
    """Remove todas as pastas __pycache__ do projeto."""
    header("PASSO 2 — Limpeza de __pycache__")
    removed = 0

    for cache_dir in root.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                ok(f"Removido: {cache_dir.relative_to(root)}/")
                removed += 1
            except Exception as e:
                err(f"Erro ao remover {cache_dir}: {e}")

    if removed == 0:
        ok("Nenhum __pycache__ encontrado")
    else:
        info(f"{removed} pasta(s) __pycache__ removida(s)")

    return removed


# -- PASSO 3: Deduplicar agents.json ------------------------------------------
def fix_agents_json(root: Path) -> dict:
    """
    Remove agentes duplicados de agents.json.
    Estratégia: mantém o ÚLTIMO agente para cada nome (versão mais recente).
    Também valida campos obrigatórios.
    """
    header("PASSO 3 — Deduplicação de agents.json")

    agents_file = root / "agents.json"
    if not agents_file.exists():
        warn("agents.json não encontrado — a saltar")
        return {"total": 0, "removed": 0, "kept": 0}

    # Fazer backup antes de alterar
    backup_file = root / "agents.json.bak"
    shutil.copy2(agents_file, backup_file)
    ok(f"Backup criado: agents.json.bak")

    try:
        with open(agents_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        err(f"agents.json tem JSON inv?lido: {e}")
        return {"total": 0, "removed": 0, "kept": 0}

    # Suporta tanto lista direta como {"agents": [...]}
    is_wrapped = isinstance(raw, dict) and "agents" in raw
    agents = raw.get("agents", raw) if is_wrapped else raw

    if not isinstance(agents, list):
        err("Formato inesperado em agents.json")
        return {"total": 0, "removed": 0, "kept": 0}

    total = len(agents)
    info(f"Total de agentes encontrados: {total}")

    # Deduplicar — mantém o último para cada nome
    seen = {}
    duplicates_found = []
    for agent in agents:
        name = agent.get("name", "").strip().lower()
        if not name:
            warn(f"Agente sem nome encontrado ? ID: {agent.get('id', 'desconhecido')}")
            continue
        if name in seen:
            duplicates_found.append(name)
            warn(f"Duplicado: '{agent.get('name')}' ? substitu?do pela vers?o mais recente")
        seen[name] = agent

    unique_agents = list(seen.values())
    removed = total - len(unique_agents)

    # Validar campos obrigatórios e normalizar
    required_fields = {"id", "name", "system_prompt", "model", "status"}
    for agent in unique_agents:
        missing = required_fields - set(agent.keys())
        if missing:
            warn(f"Agente '{agent.get('name', '?')}' sem campos: {missing} ? a adicionar defaults")
            if "status" not in agent: agent["status"] = "idle"
            if "model" not in agent:  agent["model"]  = "deepseek-chat"
            if "context" not in agent: agent["context"] = []
            if "metadata" not in agent: agent["metadata"] = {}

    # Guardar resultado
    output = {"agents": unique_agents} if is_wrapped else unique_agents
    with open(agents_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    ok(f"agents.json atualizado: {total} -> {len(unique_agents)} agentes")
    if removed > 0:
        ok(f"Removidos {removed} duplicado(s): {', '.join(set(duplicates_found))}")
    else:
        ok("Nenhum duplicado encontrado")

    return {"total": total, "removed": removed, "kept": len(unique_agents)}


# -- PASSO 4: Verificar/criar requirements.txt --------------------------------
def fix_requirements(root: Path):
    """Cria requirements.txt se não existir, baseado nos imports detetados."""
    header("PASSO 4 — requirements.txt")

    req_file = root / "requirements.txt"
    if req_file.exists():
        ok("requirements.txt já existe — a saltar")
        return

    # Dependências detetadas no código do projeto
    deps = [
        "# Gerado automaticamente por fix_repo.py",
        "requests>=2.31.0",
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.27.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.27.0",
    ]

    with open(req_file, "w", encoding="utf-8") as f:
        f.write("\n".join(deps) + "\n")

    ok("requirements.txt criado")
    info("Instala com: pip install -r requirements.txt")


# -- PASSO 5: Verificar imports críticos --------------------------------------
def verify_imports(root: Path):
    """Testa se os imports problemáticos anteriores agora funcionam."""
    header("PASSO 5 — Verificação de imports")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    modules_to_test = [
        "nexus_core",
        "memoria_permanente",
        "nexus_api",
    ]

    all_ok = True
    for mod in modules_to_test:
        mod_file = root / f"{mod}.py"
        if not mod_file.exists():
            warn(f"{mod}.py n?o encontrado ? a saltar")
            continue
        try:
            spec = importlib.util.spec_from_file_location(mod, mod_file)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            ok(f"import {mod} ? OK")
        except Exception as e:
            err(f"import {mod} ? FALHOU: {e}")
            all_ok = False

    return all_ok


# -- RELATÓRIO FINAL -----------------------------------------------------------
def print_summary(root, shadows, caches, agents_stats, imports_ok):
    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}  RELAT?RIO FINAL{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")
    print(f"  Reposit?rio  : {root}")
    print(f"  Pastas-sombra: {GREEN}{shadows} removida(s){RESET}")
    print(f"  __pycache__  : {GREEN}{caches} removido(s){RESET}")
    if agents_stats['total'] > 0:
        print(f"  Agentes JSON : {agents_stats['total']} -> {agents_stats['kept']} ({GREEN}-{agents_stats['removed']} duplicados{RESET})")
    print(f"  Imports      : {''+GREEN+'OK'+RESET if imports_ok else RED+'Com erros'+RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")

    if shadows > 0 or agents_stats['removed'] > 0:
        print(f"\n{GREEN}{BOLD}  Corre??es aplicadas com sucesso!{RESET}")
        print(f"  Testa agora com: {BOLD}python nexus.py status{RESET}\n")
    else:
        print(f"\n{GREEN}  Reposit?rio j? estava limpo!{RESET}\n")


# -- MAIN ---------------------------------------------------------------------
def main():
    print(f"\n{BOLD}{'=' * 50}")
    print("  fix_repo.py ? Corre??o autom?tica agentsbot")
    print(f"{'=' * 50}{RESET}")

    root = find_repo_root()
    info(f"Reposit?rio detetado em: {root}")

    if not any((root / f).exists() for f in ["agents.json", "nexus_core.py"]):
        err("Não parece ser o repositório agentsbot. Corre o script dentro da pasta do projeto.")
        sys.exit(1)

    shadows      = fix_shadow_folders(root)
    caches       = clean_pycache(root)
    agents_stats = fix_agents_json(root)
    fix_requirements(root)
    imports_ok   = verify_imports(root)

    print_summary(root, shadows, caches, agents_stats, imports_ok)


if __name__ == "__main__":
    main()