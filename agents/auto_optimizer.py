"""
auto_optimizer.py — Agente de Otimização Automática

Analisa código, identifica ineficiências e aplica otimizações.
"""

import ast
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

class AutoOptimizer:
    """Agente que otimiza código automaticamente"""
    
    def __init__(self):
        self.name = "[RAPIDO] Auto-Optimizer"
        self.optimizations_applied = 0
        self.issues_found: List[Dict] = []
        self.report_path = Path("memory/optimization_report.json")
        self._load_report()
    
    def _load_report(self):
        """Carrega relatório anterior"""
        if self.report_path.exists():
            try:
                data = json.loads(self.report_path.read_text())
                self.optimizations_applied = data.get("total", 0)
                self.issues_found = data.get("recent_issues", [])
            except:
                pass
    
    def _save_report(self):
        """Guarda relatório"""
        data = {
            "total": self.optimizations_applied,
            "recent_issues": self.issues_found[-20:],
            "last_scan": time.time()
        }
        self.report_path.write_text(json.dumps(data, indent=2))
    
    def analyze_file(self, filepath: str) -> List[Dict]:
        """Analisa um ficheiro Python e encontra ineficiências"""
        path = Path(filepath)
        if not path.exists():
            return [{"error": f"Ficheiro n?o encontrado: {filepath}"}]
        
        code = path.read_text()
        issues = []
        
        # 1. Verificar imports não usados
        try:
            tree = ast.parse(code)
            imports = set()
            used_names = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    used_names.add(node.attr)
            
            unused_imports = imports - used_names
            if unused_imports:
                issues.append({
                    "type": "unused_import",
                    "items": list(unused_imports),
                    "suggestion": f"Remover imports n?o usados: {', '.join(unused_imports)}"
                })
        except SyntaxError:
            issues.append({"type": "syntax_error", "suggestion": "Ficheiro tem erros de sintaxe"})
        
        # 2. Verificar loops que podem ser compreensões
        if 'for ' in code and 'append(' in code:
            issues.append({
                "type": "optimization",
                "suggestion": "Substituir loop+append por list comprehension"
            })
        
        # 3. Verificar falta de type hints em funções
        func_count = code.count('def ')
        hint_count = code.count(' -> ')
        if func_count > 0 and hint_count < func_count * 0.5:
            issues.append({
                "type": "missing_type_hints",
                "functions": func_count,
                "hinted": hint_count,
                "suggestion": "Adicionar type hints às funções"
            })
        
        # 4. Verificar docstrings
        class_count = code.count('class ')
        docstring_count = code.count('"""')
        if class_count > 0 and docstring_count < class_count:
            issues.append({
                "type": "missing_docstrings",
                "classes": class_count,
                "docstrings": docstring_count,
                "suggestion": "Adicionar docstrings às classes"
            })
        
        # 5. Verificar tamanho de funções
        lines = code.split('\n')
        current_func_lines = 0
        for line in lines:
            if line.startswith('def '):
                if current_func_lines > 50:
                    issues.append({
                        "type": "long_function",
                        "lines": current_func_lines,
                        "suggestion": "Função muito longa (>50 linhas), considerar refatorar"
                    })
                current_func_lines = 0
            elif line.startswith(('    ', '\t')):
                current_func_lines += 1
        
        self.issues_found.extend(issues)
        self._save_report()
        return issues
    
    def scan_project(self, root_dir: str = ".") -> Dict:
        """Escaneia todo o projeto por ineficiências"""
        print(f"\n{'='*60}")
        print(f"  [RAPIDO] AUTO-OPTIMIZER - Scanning {root_dir}")
        print(f"{'='*60}")
        
        total_issues = 0
        files_scanned = 0
        summary = defaultdict(int)
        
        for pyfile in Path(root_dir).rglob("*.py"):
            if 'node_modules' in str(pyfile) or '.venv' in str(pyfile):
                continue
            
            files_scanned += 1
            issues = self.analyze_file(str(pyfile))
            
            if issues:
                print(f"\n  [DOC] {pyfile.relative_to(root_dir)}")
                for issue in issues:
                    print(f"     [!]  {issue.get('type', 'issue')}: {issue.get('suggestion', '')}")
                    summary[issue['type']] += 1
                    total_issues += 1
        
        report = {
            "files_scanned": files_scanned,
            "total_issues": total_issues,
            "summary": dict(summary),
            "timestamp": time.time()
        }
        
        print(f"\n{'='*60}")
        print(f"  [DADOS] RELAT?RIO FINAL")
        print(f"  Ficheiros: {files_scanned}")
        print(f"  Issues: {total_issues}")
        for issue_type, count in summary.items():
            print(f"     {issue_type}: {count}")
        print(f"{'='*60}")
        
        return report
    
    def suggest_optimization(self, filepath: str) -> str:
        """Sugere otimização específica para um ficheiro"""
        issues = self.analyze_file(filepath)
        if not issues:
            return "[OK] Nenhuma otimização necessária!"
        
        suggestions = []
        for issue in issues:
            if issue.get('type') == 'unused_import':
                suggestions.append(f"[LIMPA] Remover imports: {', '.join(issue['items'])}")
            elif issue.get('type') == 'optimization':
                suggestions.append("[RAPIDO] Usar list comprehension em vez de loop+append")
            elif issue.get('type') == 'missing_type_hints':
                suggestions.append("[EDIT] Adicionar type hints às funções")
            elif issue.get('type') == 'missing_docstrings':
                suggestions.append("[LIVRO] Adicionar docstrings às classes")
            elif issue.get('type') == 'long_function':
                suggestions.append(f"[CORT]  Fun??o com {issue['lines']} linhas - refatorar")
        
        return "\n".join([f"  ? {s}" for s in suggestions])

# CLI
if __name__ == "__main__":
    import sys
    
    opt = AutoOptimizer()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "scan":
            root = sys.argv[2] if len(sys.argv) > 2 else "."
            opt.scan_project(root)
        elif cmd == "analyze":
            if len(sys.argv) > 2:
                issues = opt.analyze_file(sys.argv[2])
                for i in issues:
                    print(f"  [!]  {i.get('suggestion', '')}")
        elif cmd == "suggest":
            if len(sys.argv) > 2:
                print(opt.suggest_optimization(sys.argv[2]))
    else:
        # Modo autónomo
        print("\n  [IA] Modo Aut?nomo - A escanear projeto...")
        report = opt.scan_project()
        print(f"\n  [ALVO] {report['total_issues']} oportunidades de otimiza??o encontradas!")
