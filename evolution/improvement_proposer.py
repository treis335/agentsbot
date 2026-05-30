"""
evolution/improvement_proposer.py — Propõe melhorias com base nos padrões encontrados.

Usa 1 chamada DeepSeek por ciclo de análise (configurável).
Para padrões simples, usa sugestões locais sem API.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)


class ImprovementProposer:
    """
    Propõe melhorias concretas com base no relatório do LogAnalyzer.

    Estratégia:
    - Sugestões simples (erros conhecidos): resolve localmente, sem API
    - Sugestões complexas (refactoring, novos módulos): 1 chamada DeepSeek
    """

    # Templates de melhoria para padrões conhecidos (zero API)
    LOCAL_IMPROVEMENTS = {
        "fix_permission_error": {
            "title": "Verificação de permissões antes de writes",
            "description": "Adicionar check de permissões em fs_tools._run_python e _run_shell",
            "patch_hint": "Antes de open(path, 'w'), verificar os.access(path, os.W_OK)",
            "target_files": ["tools/fs_tools.py"],
            "complexity": "low",
        },
        "fix_file_not_found": {
            "title": "Auto-criação de directórios pai",
            "description": "Garantir que mkdir -p é chamado antes de criar ficheiros",
            "patch_hint": "Path(fname).parent.mkdir(parents=True, exist_ok=True) antes de write",
            "target_files": ["tools/fs_tools.py", "agents/executor.py"],
            "complexity": "low",
        },
        "fix_syntax_error": {
            "title": "Validação de sintaxe antes de executar",
            "description": "Adicionar py_compile check no executor antes de run_python",
            "patch_hint": "import py_compile; py_compile.compile(fname, doraise=True)",
            "target_files": ["agents/executor.py", "tools/fs_tools.py"],
            "complexity": "low",
        },
        "fix_import_error": {
            "title": "Auto-instalação de dependências em falta",
            "description": "Detectar ImportError e tentar pip install automaticamente",
            "patch_hint": "Em verifier.py: se ImportError detectado, extrair nome do módulo e sugerir pip install",
            "target_files": ["agents/verifier.py"],
            "complexity": "medium",
        },
        "fix_timeout": {
            "title": "Timeout adaptativo por tipo de tarefa",
            "description": "Aumentar timeout para tarefas de build/install detectadas por keywords",
            "patch_hint": "Em retry_policy.py, ajustar timeout baseado em keywords da tarefa",
            "target_files": ["agents/retry_policy.py"],
            "complexity": "low",
        },
        "fix_git_rejected": {
            "title": "Pull automático antes de push",
            "description": "Adicionar git pull --rebase antes de push em _git_commit_push",
            "patch_hint": "Em fs_tools._git_commit_push, adicionar git pull --rebase antes do push",
            "target_files": ["tools/fs_tools.py"],
            "complexity": "low",
        },
        "review_error_handling": {
            "title": "Melhoria global de tratamento de erros",
            "description": "Adicionar try/except mais granular nos executors",
            "patch_hint": "Rever agents/executor.py para capturar tipos de erro específicos",
            "target_files": ["agents/executor.py"],
            "complexity": "medium",
        },
        "clean_backlog": {
            "title": "Limpeza de tarefas falhadas no backlog",
            "description": "Arquivar tarefas com mais de 3 retries sem sucesso",
            "patch_hint": "Em autonomous_loop.py, mover para 'archived' tarefas com retry_count >= 3",
            "target_files": ["autonomous_loop.py"],
            "complexity": "low",
        },
    }

    def __init__(self):
        self.proposals_dir = Config.MEMORY_DIR / "evolution" / "proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)

    def propose(self, analysis_report: dict, use_llm: bool = True) -> list[dict]:
        """
        Gera propostas de melhoria a partir do relatório de análise.

        Args:
            analysis_report: Output do LogAnalyzer.analyze()
            use_llm: Se True, chama DeepSeek para sugestões complexas

        Returns:
            Lista de propostas ordenadas por prioridade
        """
        proposals = []
        suggestions = analysis_report.get("suggestions", [])

        # 1. Propostas locais para padrões conhecidos (zero API)
        for suggestion in suggestions:
            action = suggestion.get("action", "")
            if action in self.LOCAL_IMPROVEMENTS:
                template = self.LOCAL_IMPROVEMENTS[action]
                proposal = {
                    "id": f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{action[:20]}",
                    "source": "local_heuristic",
                    "priority": suggestion["priority"],
                    "title": template["title"],
                    "description": template["description"],
                    "patch_hint": template["patch_hint"],
                    "target_files": template["target_files"],
                    "complexity": template["complexity"],
                    "triggered_by": suggestion["type"],
                    "created_at": datetime.now().isoformat(),
                    "status": "proposed",
                }
                proposals.append(proposal)

        # 2. Proposta LLM para padrões complexos sem template local
        complex_suggestions = [
            s for s in suggestions
            if s.get("action", "") not in self.LOCAL_IMPROVEMENTS
            and s.get("priority") in ("high", "medium")
        ]

        if complex_suggestions and use_llm:
            llm_proposal = self._propose_via_llm(analysis_report, complex_suggestions)
            if llm_proposal:
                proposals.append(llm_proposal)

        # Persistir propostas
        self._save_proposals(proposals)

        logger.info(f"[ImprovementProposer] {len(proposals)} propostas geradas "
                    f"({sum(1 for p in proposals if p['source']=='local_heuristic')} locais, "
                    f"{sum(1 for p in proposals if p['source']=='llm')} LLM)")
        return proposals

    def _propose_via_llm(self, report: dict, complex_suggestions: list) -> Optional[dict]:
        """
        Usa DeepSeek para propor melhorias para padrões complexos.
        1 chamada por ciclo de análise.
        """
        try:
            import openai
            client = openai.OpenAI(
                api_key=Config.DEEPSEEK_API_KEY,
                base_url=Config.DEEPSEEK_BASE_URL,
            )

            # Resumo conciso para a API
            report_summary = {
                "failure_rate": report["totals"]["failure_rate"],
                "top_errors": [p["pattern"] for p in report["error_patterns"][:3]],
                "worst_agents": [
                    a["agent"] for a in report["agent_performance"][:2]
                    if a["success_rate"] < 0.6
                ],
                "suggestions": [s["description"] for s in complex_suggestions[:3]],
            }

            prompt = f"""Analisa este relat?rio de performance de um sistema de agentes AI e prop?e UMA melhoria concreta de c?digo:

{json.dumps(report_summary, indent=2, ensure_ascii=False)}

Responde APENAS com JSON válido (sem markdown), exactamente neste formato:
{{
  "title": "título curto da melhoria",
  "description": "descrição de 1-2 frases",
  "target_files": ["ficheiro1.py"],
  "patch_hint": "descrição técnica de como implementar (1-3 frases)",
  "complexity": "low|medium|high",
  "estimated_impact": "descrição do impacto esperado"
}}"""

            response = client.chat.completions.create(
                model=Config.DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.3,
            )

            raw = response.choices[0].message.content.strip()
            # Limpar possível markdown
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)

            return {
                "id": f"prop_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "source": "llm",
                "priority": "medium",
                "title": data.get("title", "Melhoria LLM"),
                "description": data.get("description", ""),
                "patch_hint": data.get("patch_hint", ""),
                "target_files": data.get("target_files", []),
                "complexity": data.get("complexity", "medium"),
                "estimated_impact": data.get("estimated_impact", ""),
                "triggered_by": "llm_analysis",
                "created_at": datetime.now().isoformat(),
                "status": "proposed",
            }

        except json.JSONDecodeError as e:
            logger.warning(f"[ImprovementProposer] LLM retornou JSON inv?lido: {e}")
        except Exception as e:
            logger.error(f"[ImprovementProposer] Erro na chamada LLM: {e}")

        return None

    def _save_proposals(self, proposals: list[dict]):
        """Persiste propostas no disco."""
        if not proposals:
            return
        date_str = datetime.now().strftime("%Y%m%d")
        fpath = self.proposals_dir / f"proposals_{date_str}.json"

        existing = []
        if fpath.exists():
            try:
                existing = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Deduplicar por título
        existing_titles = {p["title"] for p in existing}
        new_ones = [p for p in proposals if p["title"] not in existing_titles]
        combined = existing + new_ones

        fpath.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_pending_proposals(self, limit: int = 5) -> list[dict]:
        """Retorna propostas pendentes ordenadas por prioridade."""
        all_proposals = []
        for fpath in sorted(self.proposals_dir.glob("proposals_*.json"), reverse=True)[:7]:
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                all_proposals.extend(data)
            except Exception:
                pass

        pending = [p for p in all_proposals if p.get("status") == "proposed"]
        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending.sort(key=lambda p: priority_order.get(p.get("priority", "low"), 3))
        return pending[:limit]
