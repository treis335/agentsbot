#!/usr/bin/env python3
"""
tools/memory_compact.py — Compacta memórias antigas sem LLM.

Heurísticas locais para reduzir tamanho das memórias episódicas
preservando as entradas mais úteis (falhas únicas, lições, sucessos recentes).

Uso:
    python tools/memory_compact.py               # compactar tudo
    python tools/memory_compact.py --agent developer  # só um agente
    python tools/memory_compact.py --dry-run     # simular sem alterar
    python tools/memory_compact.py --extract-lessons  # só extrair lições
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from memory.lesson_extractor import LessonExtractor


def compact_agent_memory(agent_file: Path, dry_run: bool = False) -> dict:
    """
    Compacta memória episódica de um agente.

    Regras de compactação:
    - Manter TODAS as entradas dos últimos 7 dias
    - Para entradas antigas: manter só as que têm lição ou são falhas únicas
    - Manter sempre os últimos 20 episódios independente da data
    - Limite máximo: 150 episódios
    """
    try:
        episodes = json.loads(agent_file.read_text(encoding="utf-8"))
    except Exception as e:
        return {"agent": agent_file.stem, "error": str(e)}

    original_count = len(episodes)
    if original_count == 0:
        return {"agent": agent_file.stem, "original": 0, "compacted": 0, "removed": 0}

    cutoff = datetime.now() - timedelta(days=7)
    recent_20 = episodes[-20:]
    recent_20_ids = {id(ep) for ep in recent_20}  # Python object identity

    kept = []
    removed = 0

    for ep in episodes:
        # Sempre manter os últimos 20
        if id(ep) in recent_20_ids:
            kept.append(ep)
            continue

        # Verificar se é recente (últimos 7 dias)
        try:
            ts = datetime.fromisoformat(ep.get("timestamp", "2000-01-01"))
            if ts > cutoff:
                kept.append(ep)
                continue
        except Exception:
            pass

        # Para entradas antigas: só manter se tem lição ou é falha com info útil
        has_lesson = bool(ep.get("lesson"))
        is_failure = not ep.get("success", True)
        has_useful_error = is_failure and len(ep.get("episode", {}).get("result", "")) > 20

        if has_lesson or has_useful_error:
            kept.append(ep)
        else:
            removed += 1

    # Aplicar limite máximo de 150
    if len(kept) > 150:
        overflow = len(kept) - 150
        # Remover as mais antigas sem lição
        no_lesson = [ep for ep in kept if not ep.get("lesson")]
        to_remove = no_lesson[:overflow]
        to_remove_set = {id(ep) for ep in to_remove}
        kept = [ep for ep in kept if id(ep) not in to_remove_set]
        removed += len(to_remove)

    result = {
        "agent": agent_file.stem,
        "original": original_count,
        "compacted": len(kept),
        "removed": removed,
        "reduction_pct": round(removed / original_count * 100, 1) if original_count else 0,
    }

    if not dry_run and removed > 0:
        agent_file.write_text(
            json.dumps(kept, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  ✅ {agent_file.stem}: {original_count} → {len(kept)} episódios (-{removed})")
    elif dry_run:
        print(f"  🔍 [DRY] {agent_file.stem}: {original_count} → {len(kept)} (-{removed})")
    else:
        print(f"  ⏭️  {agent_file.stem}: nada para compactar ({original_count} episódios)")

    return result


def main():
    parser = argparse.ArgumentParser(description="Compactação de memórias episódicas")
    parser.add_argument("--agent", help="Nome do agente (default: todos)")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem alterar ficheiros")
    parser.add_argument("--extract-lessons", action="store_true", help="Extrair lições antes de compactar")
    args = parser.parse_args()

    episodic_dir = Config.MEMORY_DIR / "episodica"

    if not episodic_dir.exists():
        print(f"❌ Directório não existe: {episodic_dir}")
        sys.exit(1)

    # Extrair lições primeiro se pedido
    if args.extract_lessons:
        print("\n📚 A extrair lições dos logs episódicos...")
        extractor = LessonExtractor()
        result = extractor.run()
        print(f"  ✅ {result['extracted']} lições extraídas → {result['saved_to']}\n")

    print(f"\n🗜️  A compactar memórias episódicas{' (DRY RUN)' if args.dry_run else ''}...\n")

    # Seleccionar ficheiros
    if args.agent:
        files = list(episodic_dir.glob(f"{args.agent}.json"))
        if not files:
            print(f"❌ Agente não encontrado: {args.agent}")
            sys.exit(1)
    else:
        files = list(episodic_dir.glob("*.json"))

    if not files:
        print("Nenhum ficheiro de memória encontrado.")
        sys.exit(0)

    total_removed = 0
    total_original = 0

    for f in sorted(files):
        result = compact_agent_memory(f, dry_run=args.dry_run)
        total_removed += result.get("removed", 0)
        total_original += result.get("original", 0)

    print(f"\n📊 Total: {total_original} episódios → removidos {total_removed} "
          f"({round(total_removed/total_original*100, 1) if total_original else 0}%)")

    if args.dry_run:
        print("   (DRY RUN — nenhum ficheiro alterado)")


if __name__ == "__main__":
    main()
