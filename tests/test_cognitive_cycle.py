"""
test_cognitive_cycle.py - Testes para o CognitiveCycle
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pytest

from core.cognitive_cycle import CognitiveCycle, MAX_IDENTICAL_ACTIONS, MAX_CYCLES_BEFORE_LEARN


@pytest.fixture
def cycle():
    """Cria uma instância limpa de CognitiveCycle para cada teste."""
    # Guardar caminho original
    from core import cognitive_cycle as cc
    original_memory_dir = cc.MEMORY_DIR
    original_state_file = cc.CYCLE_STATE_FILE
    
    # Criar diretório temporário
    tmp_dir = Path(tempfile.mkdtemp())
    cc.MEMORY_DIR = tmp_dir
    cc.CYCLE_STATE_FILE = tmp_dir / "cycle_state.json"
    
    instance = CognitiveCycle()
    
    yield instance
    
    # Restaurar
    cc.MEMORY_DIR = original_memory_dir
    cc.CYCLE_STATE_FILE = original_state_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


class TestCognitiveCycle:
    
    def test_run_cycle_nao_lanca_excecoes(self, cycle):
        """Testar que run_cycle() não lança exceções."""
        try:
            result = cycle.run_cycle()
            assert result is not None
            assert "status" in result
            assert result["status"] == "ok"
        except Exception as e:
            pytest.fail(f"run_cycle() lan?ou exce??o: {e}")
    
    def test_anti_loop_deteta_acoes_identicas(self, cycle):
        """Testar que o anti-loop deteta ações idênticas e ativa o mecanismo."""
        # MAX_IDENTICAL_ACTIONS = 3, então após 3 ações iguais seguidas o loop é detetado
        # O 1º ciclo: last_action_key=None, action=analyze -> contador=0
        # O 2º ciclo: last_action_key=analyze, action=analyze -> contador=1
        # O 3º ciclo: last_action_key=analyze, action=analyze -> contador=2
        # O 4º ciclo: last_action_key=analyze, action=analyze -> contador=3 >= 3 -> loop detetado!
        
        loop_detected = False
        for i in range(MAX_IDENTICAL_ACTIONS + 2):
            result = cycle.run_cycle()
            if result.get("loop_detected"):
                loop_detected = True
                break
        
        assert loop_detected, (
            f"Anti-loop n?o detetou {MAX_IDENTICAL_ACTIONS + 2} a??es id?nticas"
        )
    
    def test_anti_loop_trava_no_inicio_do_ciclo_seguinte(self, cycle):
        """Testar que se o contador ainda estiver alto, trava no início."""
        # Forçar o estado para simular que o anti-loop já devia ter ativado
        cycle.state["identical_action_count"] = MAX_IDENTICAL_ACTIONS
        
        # O próximo run_cycle deve travar antes de executar
        result = cycle.run_cycle()
        assert result["status"] == "travao_ativado", (
            f"Esperado 'travao_ativado', obtido '{result['status']}'"
        )
        assert "insight" in result
        assert result["insight"]["observation"] == "loop_detetado"
    
    def test_estado_persiste_corretamente(self, cycle):
        """Testar que o estado persiste corretamente entre ciclos."""
        # Executar alguns ciclos
        for i in range(3):
            cycle.run_cycle()
        
        # Verificar que o estado foi guardado
        from core.cognitive_cycle import CYCLE_STATE_FILE
        assert CYCLE_STATE_FILE.exists(), "Ficheiro de estado não foi criado"
        
        with open(CYCLE_STATE_FILE) as f:
            saved_state = json.load(f)
        
        # Verificar campos essenciais
        assert "total_cycles" in saved_state
        assert saved_state["total_cycles"] == 3
        assert "last_action_key" in saved_state
        assert "identical_action_count" in saved_state
        assert "insights" in saved_state
        assert "last_learn_time" in saved_state
        
        # Verificar que o estado carregado corresponde
        assert cycle.state["total_cycles"] == 3
    
    def test_max_cycles_before_learn_config(self, cycle):
        """Testar que MAX_CYCLES_BEFORE_LEARN é usado (aprender a cada N ciclos)."""
        # Executar MAX_CYCLES_BEFORE_LEARN ciclos
        for i in range(MAX_CYCLES_BEFORE_LEARN):
            cycle.run_cycle()
        
        # Deve ter pelo menos um insight (aprender periódico)
        assert len(cycle.state["insights"]) >= 1
    
    def test_run_cycle_com_contexto(self, cycle):
        """Testar run_cycle com contexto personalizado."""
        result = cycle.run_cycle(context="test_context")
        assert result["status"] == "ok"
        assert result["cycle"] == 1
