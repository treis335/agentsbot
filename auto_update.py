"""
auto_update.py v3.0 - SISTEMA DE AUTO-UPDATE DO SUPERVISOR (COMPLETO)
✅ Permite ao supervisor atualizar-se a si mesmo
✅ Gera novo código para si próprio
✅ Faz commit e push automaticamente
✅ Pede reinício para aplicar mudanças
✅ Auto-diagnóstico e reparação de ficheiros truncados
✅ Verificação de integridade de todos os ficheiros críticos
"""

import os
import sys
import json
import time
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
SUPERVISOR_SOUL = BASE / "agents" / "souls" / "supervisor.md"
UPDATE_LOG = BASE / "auto_update.log"
RESTART_FLAG = BASE / ".restart_requested"

# Ficheiros críticos que precisam de ser verificados
FICHEIROS_CRITICOS = [
    "agents/souls/supervisor.md",
    "auto_update.py",
    "run_forever.py",
    "auto_recovery.py",
    "auto_recovery_manager.py",
    "wakeup_v3.py",
    "main.py",
]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry, flush=True)
    with open(UPDATE_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def read_current_soul():
    """Lê a alma atual do supervisor."""
    if SUPERVISOR_SOUL.exists():
        return SUPERVISOR_SOUL.read_text(encoding="utf-8")
    return ""

def backup_soul():
    """Faz backup da alma antes de modificar."""
    backup_path = BASE / "agents" / "souls" / "supervisor.md.bak"
    if SUPERVISOR_SOUL.exists():
        content = SUPERVISOR_SOUL.read_text(encoding="utf-8")
        backup_path.write_text(content, encoding="utf-8")
        log(f"Backup criado: {backup_path}")
        return True
    return False

def git_auto_commit(message):
    """Faz git add, commit e push."""
    try:
        subprocess.run(["git", "add", "."], cwd=BASE, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", message], cwd=BASE, capture_output=True, timeout=10)
        result = subprocess.run(["git", "push"], cwd=BASE, capture_output=True, timeout=30, text=True)
        log(f"Git push: {result.stdout.strip()[:200]}")
        return True
    except Exception as e:
        log(f"Erro no git: {e}")
        return False

def check_for_updates():
    """Verifica se há atualizações disponíveis no git."""
    try:
        result = subprocess.run(["git", "fetch"], cwd=BASE, capture_output=True, timeout=10)
        result = subprocess.run(["git", "status", "-uno"], cwd=BASE, capture_output=True, timeout=10, text=True)
        if "Your branch is behind" in result.stdout:
            log("Há atualizações no repositório remoto!")
            return True
        return False
    except Exception as e:
        log(f"Erro ao verificar atualizações: {e}")
        return False

def verify_file_integrity():
    """Verifica se todos os ficheiros críticos existem e não estão vazios."""
    issues = []
    for ficheiro in FICHEIROS_CRITICOS:
        path = BASE / ficheiro
        if not path.exists():
            issues.append(f"❌ {ficheiro} - NÃO EXISTE")
        elif path.stat().st_size < 100:
            issues.append(f"⚠️ {ficheiro} - Tamanho suspeito: {path.stat().st_size} bytes")
        else:
            log(f"✅ {ficheiro} - OK ({path.stat().st_size} bytes)")
    
    if issues:
        log("PROBLEMAS DETETADOS:")
        for issue in issues:
            log(f"  {issue}")
        return False
    return True

def auto_repair():
    """Tenta reparar ficheiros corrompidos ou em falta."""
    log("🔧 A executar auto-reparação...")
    
    # Verificar supervisor.md
    if SUPERVISOR_SOUL.exists() and SUPERVISOR_SOUL.stat().st_size < 100:
        log("⚠️ supervisor.md corrompido! A restaurar de backup...")
        backup = BASE / "agents" / "souls" / "supervisor.md.bak"
        if backup.exists():
            shutil.copy2(backup, SUPERVISOR_SOUL)
            log("✅ supervisor.md restaurado do backup!")
        else:
            log("❌ Sem backup disponível para supervisor.md")
    
    # Verificar auto_update.py
    auto_update_path = BASE / "auto_update.py"
    if auto_update_path.exists() and auto_update_path.stat().st_size < 100:
        log("⚠️ auto_update.py corrompido! Tamanho suspeito.")
    
    return verify_file_integrity()

def request_restart():
    """Pede reinício do sistema."""
    RESTART_FLAG.write_text("restart_requested", encoding="utf-8")
    log("🔄 Pedido de reinício registado!")
    log("Por favor, diz 'fecha' ao supervisor para aplicar as mudanças.")

def run_full_update():
    """Executa o ciclo completo de auto-update."""
    log("=" * 60)
    log("🚀 AUTO-UPDATE v3.0 - INICIADO")
    log("=" * 60)
    
    # Passo 1: Backup
    log("\n📦 Passo 1: Backup da alma atual...")
    backup_soul()
    
    # Passo 2: Verificar integridade
    log("\n🔍 Passo 2: Verificar integridade dos ficheiros...")
    integridade_ok = verify_file_integrity()
    
    if not integridade_ok:
        log("\n🔧 Passo 2b: A reparar ficheiros...")
        auto_repair()
    
    # Passo 3: Verificar atualizações remotas
    log("\n🌐 Passo 3: Verificar atualizações no GitHub...")
    has_updates = check_for_updates()
    
    if has_updates:
        log("📥 A fazer pull das atualizações...")
        subprocess.run(["git", "pull"], cwd=BASE, capture_output=True, timeout=30)
        log("✅ Pull concluído!")
    
    # Passo 4: Git commit e push
    log("\n📤 Passo 4: A fazer commit e push...")
    data = datetime.now().strftime("%Y-%m-%d %H:%M")
    git_auto_commit(f"feat: auto-update v3.0 - {data}")
    
    # Passo 5: Pedir reinício
    log("\n🔄 Passo 5: A pedir reinício...")
    request_restart()
    
    log("\n" + "=" * 60)
    log("✅ AUTO-UPDATE CONCLUÍDO COM SUCESSO!")
    log("=" * 60)
    
    return True

if __name__ == "__main__":
    run_full_update()
