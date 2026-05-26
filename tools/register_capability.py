#!/usr/bin/env python3
"""
tools/register_capability.py — Ferramenta para agentes auto-registarem skills.

Uso CLI:
    python tools/register_capability.py --agent developer --skill testing --keywords "testar,test,pytest"
    python tools/register_capability.py --list
    python tools/register_capability.py --scores "implementar função de login"
"""

import argparse
import sys
import os

# Adicionar root ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.capability_registry import get_registry


def main():
    parser = argparse.ArgumentParser(description="Gestão de capabilities dos agentes")
    parser.add_argument("--agent", help="Nome do agente")
    parser.add_argument("--skill", help="Nome da skill a registar")
    parser.add_argument("--keywords", help="Keywords separadas por vírgula")
    parser.add_argument("--list", action="store_true", help="Listar todos os agentes e skills")
    parser.add_argument("--scores", metavar="TASK", help="Calcular scores para uma tarefa")
    parser.add_argument("--match", metavar="TASK", help="Encontrar melhor agente para tarefa")

    args = parser.parse_args()
    registry = get_registry()

    if args.list:
        print("\n📋 Agentes registados:\n")
        for agent in registry.list_agents():
            skills = registry.get_agent_skills(agent)
            desc = registry.get_agent_description(agent)
            print(f"  🤖 {agent}: {desc}")
            print(f"     Skills: {', '.join(skills) if skills else '(nenhuma)'}\n")
        return

    if args.scores:
        print(f"\n📊 Scores para: '{args.scores}'\n")
        scores = registry.score_all(args.scores)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for agent, score in ranked:
            bar = "█" * max(0, int(score))
            print(f"  {agent:20s} {score:5.1f}  {bar}")
        return

    if args.match:
        best = registry.match(args.match)
        print(f"\n✅ Melhor agente para '{args.match}': {best}\n")
        return

    if args.agent and args.skill:
        keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
        registry.register_skill(args.agent, args.skill, keywords)
        print(f"✅ Skill '{args.skill}' registada para '{args.agent}'")
        if keywords:
            print(f"   Keywords: {', '.join(keywords)}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
