"""
deploy_to_main.py
Script para organizar e fazer push final para a branch main.
Executa: status -> add -> commit -> pull rebase -> push
"""

import subprocess
import sys
from datetime import datetime


def run(cmd: str, capture: bool = True) -> tuple[int, str]:
    """Executa um comando shell e retorna (returncode, output)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture,
        text=True, encoding="utf-8"
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


def section(title: str):
    print(f"\n{'-' * 50}")
    print(f"  {title}")
    print('-' * 50)


def main():
    commit_msg = (
        f"feat: restaurar supervisor.md + sistema de checkpoint\n\n"
        f"- Restaurado agents/souls/supervisor.md (ficheiro estava truncado)\n"
        f"- Adicionado checkpoint_system.py com IterationManager e AntiLoopGuard\n"
        f"- Sistema de checkpoint automático a cada 5 iterações\n"
        f"- Anti-loop handler com registo de erros em memory/errors.md\n"
        f"- Resume automático de tarefas interrompidas\n\n"
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    # -- 1. Status atual --------------------------------------------------------
    section("1/5 — Git Status")
    code, out = run("git status")
    print(out)
    if "nothing to commit" in out:
        print("\n[OK] Nada para commitar. Repositório já está atualizado.")
        sys.exit(0)

    # -- 2. Adicionar ficheiros -------------------------------------------------
    section("2/5 — Git Add")
    code, out = run("git add .")
    if code != 0:
        print(f"[X] Erro no git add:\n{out}")
        sys.exit(1)
    print("[OK] Todos os ficheiros adicionados.")

    # -- 3. Commit --------------------------------------------------------------
    section("3/5 — Git Commit")
    code, out = run(f'git commit -m "{commit_msg}"')
    if code != 0:
        print(f"[X] Erro no commit:\n{out}")
        sys.exit(1)
    print(f"[OK] Commit criado.")
    print(out.split("\n")[0])  # Mostrar primeira linha do output

    # -- 4. Pull com rebase (evitar conflitos) ----------------------------------
    section("4/5 — Git Pull --rebase")
    code, out = run("git pull origin main --rebase")
    if code != 0:
        print(f"[!]  Pull com rebase falhou:\n{out}")
        print("\nTentando resolver automaticamente...")
        code2, out2 = run("git rebase --abort")
        print(f"Rebase abortado. Por favor resolver conflitos manualmente:")
        print(f"  1. git pull origin main")
        print(f"  2. Resolver conflitos")
        print(f"  3. git push origin main")
        sys.exit(1)
    print("[OK] Pull com rebase concluído.")

    # -- 5. Push ----------------------------------------------------------------
    section("5/5 — Git Push")
    code, out = run("git push origin main")
    if code != 0:
        print(f"[X] Erro no push:\n{out}")
        print("\nPossíveis causas:")
        print("  - Sem autenticação Git configurada")
        print("  - Branch protegida")
        print("  - Sem permissões no repositório")
        sys.exit(1)
    print("[OK] Push concluído com sucesso!")
    print(out)

    # -- Sumário ----------------------------------------------------------------
    section("[OK] DEPLOY CONCLUÍDO")
    print(f"  Repositório: https://github.com/treis335/agentsbot")
    print(f"  Branch: main")
    print(f"  Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n  Ficheiros deployados:")
    print(f"    • agents/souls/supervisor.md  (restaurado)")
    print(f"    • checkpoint_system.py         (novo)")


if __name__ == "__main__":
    main()
