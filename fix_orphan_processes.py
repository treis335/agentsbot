"""
fix_orphan_processes.py — Mata processos python3.13.exe órfãos
e garante que apenas 1 instância do main.py está ativa.
Execução: python fix_orphan_processes.py
"""
import subprocess
import os
import json
import time

CWD = os.path.dirname(os.path.abspath(__file__))

def get_orphan_pids():
    """Identifica PIDs python3.13.exe que não são o dono do lock nem este script."""
    current_pid = os.getpid()
    
    # Ler o PID dono do lock
    lock_pid = None
    lock_path = os.path.join(CWD, '.instance.lock')
    if os.path.exists(lock_path):
        try:
            lock_pid = int(open(lock_path).read().strip())
        except:
            pass
    
    # Listar processos python3.13.exe
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq python3.13.exe'],
        capture_output=True, text=True, timeout=5
    )
    
    pids = []
    for line in result.stdout.split('\n'):
        if 'python3.13.exe' in line:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    pid = int(parts[1])
                    pids.append(pid)
                except:
                    pass
    
    # Órfãos = todos menos o dono do lock e este script
    orphans = [p for p in pids if p != lock_pid and p != current_pid]
    return orphans, lock_pid, current_pid

def kill_orphans():
    orphans, lock_pid, current_pid = get_orphan_pids()
    
    print(f"[LOCK] PID dono: {lock_pid}")
    print(f"[THIS] PID atual: {current_pid}")
    print(f"[PIDS] Total python3.13.exe: {len(orphans) + (1 if lock_pid else 0) + 1}")
    
    if not orphans:
        print("[OK] Nenhum processo órfão encontrado.")
        return 0
    
    killed = 0
    for pid in orphans:
        try:
            print(f"[KILL] A matar PID {pid}...")
            r = subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                             capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                killed += 1
                print(f"  ✅ Morto!")
            else:
                print(f"  ⚠️  {r.stderr.strip()}")
        except Exception as e:
            print(f"  ❌ Erro: {e}")
    
    return killed

if __name__ == '__main__':
    print("=" * 50)
    print("🔧 CORREÇÃO DE PROCESSOS ÓRFÃOS")
    print("=" * 50)
    killed = kill_orphans()
    print(f"\nTotal: {killed} processos mortos.")
    
    # Se matámos algum, verificar resultado
    if killed > 0:
        time.sleep(1)
        orphans, _, _ = get_orphan_pids()
        if orphans:
            print(f"⚠️  Ainda {len(orphans)} órfãos. A executar novamente...")
            kill_orphans()
        else:
            print("✅ Sistema limpo!")
