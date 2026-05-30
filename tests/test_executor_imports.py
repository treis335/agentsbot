"""
tests/test_executor_imports.py — Valida que todos os imports do AgentExecutor funcionam.

Testa:
- Import de tools (TOOLS, execute_tool)
- Import de memory.episodica (EpisodicMemory)
- Import de security.auditor (AuditLogger)
- Import de monitoring.metrics (MetricsCollector)
- Import de agents.verifier (tool_verifier)
- Import de agents.retry_policy (retry_policy)
- Import final de agents.executor (AgentExecutor)
"""
import sys
import importlib
from pathlib import Path

# Adiciona a raiz do projecto ao path
BASE_DIR = Path(__file__).parent.parent.resolve()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def test_import_tools():
    """TOOLS e execute_tool devem ser importáveis de tools."""
    from tools import TOOLS, execute_tool
    assert isinstance(TOOLS, list), "TOOLS deve ser uma lista"
    assert len(TOOLS) > 0, "TOOLS não pode estar vazia"
    assert callable(execute_tool), "execute_tool deve ser uma função"


def test_import_episodic_memory():
    """EpisodicMemory deve ser importável de memory.episodica."""
    from memory.episodica import EpisodicMemory
    # Testa instanciação
    mem = EpisodicMemory(agent_id="test_agent")
    assert mem.agent_id == "test_agent"
    assert hasattr(mem, "record"), "EpisodicMemory deve ter método record"
    assert hasattr(mem, "get_recent"), "EpisodicMemory deve ter método get_recent"


def test_import_audit_logger():
    """AuditLogger deve ser importável de security.auditor."""
    from security.auditor import AuditLogger
    audit = AuditLogger()
    assert hasattr(audit, "log"), "AuditLogger deve ter método log"
    assert hasattr(audit, "get_logs"), "AuditLogger deve ter método get_logs"


def test_import_metrics_collector():
    """MetricsCollector deve ser importável de monitoring.metrics."""
    from monitoring.metrics import MetricsCollector
    metrics = MetricsCollector()
    assert hasattr(metrics, "track_tool_call"), "MetricsCollector deve ter track_tool_call"
    assert hasattr(metrics, "get_report"), "MetricsCollector deve ter get_report"


def test_import_verifier():
    """tool_verifier deve ser importável de agents.verifier."""
    from agents.verifier import verifier as tool_verifier
    assert hasattr(tool_verifier, "verify"), "tool_verifier deve ter método verify"


def test_import_retry_policy():
    """retry_policy deve ser importável de agents.retry_policy."""
    from agents.retry_policy import retry_policy
    assert hasattr(retry_policy, "new_state"), "retry_policy deve ter método new_state"
    assert hasattr(retry_policy, "should_escalate"), "retry_policy deve ter should_escalate"


def test_import_agent_executor():
    """AgentExecutor deve ser importável de agents.executor."""
    from agents.executor import AgentExecutor
    assert AgentExecutor.__name__ == "AgentExecutor"
    # Não instanciamos porque precisa de Config e soul files


def test_all_imports_together():
    """Todos os imports devem funcionar em conjunto (simula o topo do executor.py)."""
    from tools import TOOLS, execute_tool
    from memory.episodica import EpisodicMemory
    from security.auditor import AuditLogger
    from monitoring.metrics import MetricsCollector
    from agents.verifier import verifier as tool_verifier
    from agents.retry_policy import retry_policy
    from agents.executor import AgentExecutor

    # Verifica que todos os símbolos existem
    assert TOOLS is not None
    assert execute_tool is not None
    assert EpisodicMemory is not None
    assert AuditLogger is not None
    assert MetricsCollector is not None
    assert tool_verifier is not None
    assert retry_policy is not None
    assert AgentExecutor is not None
