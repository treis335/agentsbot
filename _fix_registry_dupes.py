"""
Script de correção e validação do registry de agentes.
Remove duplicatas e adiciona validação para evitar novas.

Uso:
    python _fix_registry_dupes.py          # Corrige e valida
    python _fix_registry_dupes.py --check  # Apenas verifica
"""
import json
import sys
from pathlib import Path

REGISTRY_FILE = Path("agents/registry/agents.json")


def load_registry() -> list:
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(data: list):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Guardados {len(data)} agentes em {REGISTRY_FILE}")


def check_duplicates(data: list) -> list:
    """Devolve lista de nomes duplicados."""
    from collections import Counter
    names = [a.get("name", "unknown") for a in data]
    return [name for name, count in Counter(names).items() if count > 1]


def deduplicate(data: list) -> list:
    """Remove duplicatas mantendo a primeira ocorrência."""
    seen = set()
    result = []
    removed = []
    for agent in data:
        name = agent.get("name", "unknown")
        if name not in seen:
            seen.add(name)
            result.append(agent)
        else:
            removed.append(name)
    if removed:
        print(f"🧹 Removidos {len(removed)} duplicados: {', '.join(removed)}")
    return result


def main():
    check_only = "--check" in sys.argv

    data = load_registry()
    print(f"📊 Registry atual: {len(data)} agentes")

    dupes = check_duplicates(data)
    if dupes:
        print(f"⚠️  {len(dupes)} nomes duplicados: {', '.join(dupes)}")
        if check_only:
            print("🔴 Validação FALHOU — existem duplicatas!")
            sys.exit(1)
        else:
            data = deduplicate(data)
            save_registry(data)
    else:
        print("✅ Nenhuma duplicata encontrada — registry saudável!")

    # Verificar novamente
    dupes = check_duplicates(data)
    if dupes:
        print(f"🔴 Ainda existem duplicatas após correção: {dupes}")
        sys.exit(1)

    print("✅ Validação completa — registry OK!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
