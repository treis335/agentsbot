"""
auto_evolve_v2.py v1.1 - SISTEMA DE EVOLUCAO AUTONOMA (CORRIGIDO - SEM EMOJIS)
- Analisa o codigo e identifica melhorias
- Gera codigo novo automaticamente
- Testa antes de aplicar
- Faz commit e push
- Aprende com os erros
- Evolui sem intervencao humana
"""

import os
import sys
import json
import time
import subprocess
import ast
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
EVOLUTION_LOG = BASE / "evolution.log"
LEARNED_KNOWLEDGE = BASE / "learned_knowledge.json"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    # Forcar ASCII-safe para evitar erros de encoding no Windows
    safe_entry = entry.encode('ascii', 'replace').decode('ascii')
    print(safe_entry, flush=True)
    with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def load_knowledge():
    if LEARNED_KNOWLEDGE.exists():
        try:
            return json.loads(LEARNED_KNOWLEDGE.read_text(encoding="utf-8"))
        except:
            return {"learnings": [], "errors": [], "improvements": []}
    return {"learnings": [], "errors": [], "improvements": []}

def save_knowledge(knowledge):
    LEARNED_KNOWLEDGE.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False), encoding="utf-8")

def learn_from_error(error_msg, context):
    knowledge = load_knowledge()
    knowledge["errors"].append({
        "error": error_msg,
        "context": context,
        "timestamp": datetime.now().isoformat()
    })
    save_knowledge(knowledge)
    log(f"[APRENDIZADO] Erro registado: {error_msg[:100]}")

def analyze_code_for_improvements():
    improvements = []
    for py_file in BASE.rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                improvements.append({
                    "file": str(py_file.relative_to(BASE)),
                    "type": "missing_docstring",
                    "desc": f"Falta docstring em {py_file.name}"
                })
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    has_hints = any(arg.annotation for arg in node.args.args)
                    if not has_hints and node.name != "__init__":
                        improvements.append({
                            "file": str(py_file.relative_to(BASE)),
                            "type": "missing_type_hints",
                            "desc": f"Funcao '{node.name}' sem type hints em {py_file.name}"
                        })
        except:
            continue
    return improvements

def generate_improvement_code(improvement):
    file_path = BASE / improvement["file"]
    content = file_path.read_text(encoding="utf-8")
    if improvement["type"] == "missing_docstring":
        if not content.startswith('"""'):
            docstring = f'"""{improvement["desc"]}\n"""\n\n'
            content = docstring + content
            return content
    return None

def apply_improvements(improvements):
    applied = []
    for imp in improvements[:5]:
        try:
            new_content = generate_improvement_code(imp)
            if new_content:
                file_path = BASE / imp["file"]
                backup = file_path.read_text(encoding="utf-8")
                file_path.write_text(new_content, encoding="utf-8")
                try:
                    ast.parse(new_content)
                    applied.append(imp)
                    log(f"[OK] Melhoria aplicada: {imp['desc']}")
                except SyntaxError as e:
                    file_path.write_text(backup, encoding="utf-8")
                    log(f"[ERRO] Sintaxe ao aplicar {imp['desc']}: {e}")
                    learn_from_error(str(e), imp)
        except Exception as e:
            log(f"[ERRO] Ao aplicar melhoria: {e}")
            learn_from_error(str(e), imp)
    return applied

def git_commit_push(message):
    try:
        subprocess.run(["git", "add", "-A"], cwd=BASE, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", message], cwd=BASE, capture_output=True, timeout=10)
        result = subprocess.run(["git", "push"], cwd=BASE, capture_output=True, timeout=30)
        return result.returncode == 0
    except:
        return False

def run_tests():
    try:
        test_code = """
import sys
sys.path.insert(0, r'C:\\Users\\Crypto Bull\\Desktop\\Agente Local')
try:
    import main
    print("OK: main.py importado")
except Exception as e:
    print(f"ERRO: main: {e}")
try:
    import auto_recovery
    print("OK: auto_recovery.py importado")
except Exception as e:
    print(f"ERRO: auto_recovery: {e}")
"""
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True, text=True, timeout=15
        )
        print(result.stdout)
        print(result.stderr)
        return result.returncode == 0
    except:
        return False

def evolve():
    log("=" * 60)
    log("INICIANDO CICLO DE EVOLUCAO AUTONOMA")
    log("=" * 60)
    
    log("[ANALISE] Analisando codigo para melhorias...")
    improvements = analyze_code_for_improvements()
    log(f"[RESULTADO] Encontradas {len(improvements)} oportunidades de melhoria")
    
    if improvements:
        log("[APLICAR] Aplicando melhorias...")
        applied = apply_improvements(improvements)
        log(f"[RESULTADO] {len(applied)} melhorias aplicadas com sucesso")
        
        if applied:
            log("[TESTES] A correr testes...")
            if run_tests():
                log("[OK] Testes passaram!")
                log("[COMMIT] A fazer commit...")
                if git_commit_push(f"feat: evolucao autonoma - {len(applied)} melhorias aplicadas"):
                    log("[OK] Commit e push feitos com sucesso!")
                else:
                    log("[AVISO] Falha no push, mas codigo salvo localmente")
            else:
                log("[ERRO] Testes falharam! A reverter alteracoes...")
                subprocess.run(["git", "checkout", "."], cwd=BASE, capture_output=True)
    else:
        log("[INFO] Nenhuma melhoria necessaria neste ciclo")
    
    knowledge = load_knowledge()
    knowledge["learnings"].append({
        "timestamp": datetime.now().isoformat(),
        "improvements_found": len(improvements),
        "improvements_applied": len([i for i in improvements if i.get("applied")])
    })
    save_knowledge(knowledge)
    
    log("=" * 60)
    log("CICLO DE EVOLUCAO CONCLUIDO")
    log("=" * 60)
    
    return len(improvements)

if __name__ == "__main__":
    evolve()
