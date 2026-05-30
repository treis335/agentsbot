"""
Testes para o MemoryHub - Sistema Unificado de Memória
"""
import os
import sys
import json
import tempfile
import unittest

# Adicionar projecto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.memory_hub import MemoryHub


class TestMemoryHub(unittest.TestCase):
    """Testes para o MemoryHub."""

    def setUp(self):
        """Preparar ambiente de teste."""
        self.hub = MemoryHub()
        # Usar ficheiro temporário para não poluir dados reais
        self._original_file = self.hub.filepath
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        self.hub.filepath = self.tmp.name
        self.hub.clear()

    def tearDown(self):
        """Limpar após teste."""
        self.hub.filepath = self._original_file
        try:
            os.unlink(self.tmp.name)
        except:
            pass

    def test_store_chat(self):
        """Deve armazenar mensagens de chat."""
        self.hub.store_chat("user", "Olá")
        self.hub.store_chat("assistant", "Olá, como posso ajudar?")
        entries = self.hub._load_all()
        chats = [e for e in entries if e.get("type") == "chat"]
        self.assertEqual(len(chats), 2)
        self.assertEqual(chats[0]["data"]["role"], "user")
        self.assertEqual(chats[0]["data"]["content"], "Olá")
        self.assertEqual(chats[1]["data"]["role"], "assistant")

    def test_store_episode(self):
        """Deve armazenar episódios de agentes."""
        self.hub.store_episode("executor", "calcular_imposto", {"resultado": 1500})
        entries = self.hub._load_all()
        eps = [e for e in entries if e.get("type") == "episode"]
        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0]["data"]["agent_id"], "executor")
        self.assertEqual(eps[0]["data"]["task"], "calcular_imposto")
        self.assertIn("1500", eps[0]["data"]["result"])

    def test_store_knowledge(self):
        """Deve armazenar conhecimento semântico."""
        self.hub.store_knowledge("python", "Python é uma linguagem de programação")
        entries = self.hub._load_all()
        kn = [e for e in entries if e.get("type") == "knowledge"]
        self.assertEqual(len(kn), 1)
        self.assertEqual(kn[0]["data"]["topic"], "python")
        self.assertEqual(kn[0]["data"]["content"], "Python é uma linguagem de programação")

    def test_get_context_returns_string(self):
        """get_context deve devolver string formatada."""
        self.hub.store_chat("user", "teste")
        self.hub.store_episode("executor", "task1", "ok")
        self.hub.store_knowledge("tema", "conteudo")
        ctx = self.hub.get_context("executor", n=10)
        self.assertIsInstance(ctx, str)
        self.assertGreater(len(ctx), 0)
        self.assertIn('CONVERSAS RECENTES', ctx)
        self.assertIn('EXPERIENCIAS RECENTES', ctx)
        self.assertIn('CONHECIMENTO', ctx)

    def test_get_context_filters_by_agent(self):
        """get_context deve filtrar episódios por agente."""
        self.hub.store_episode("agente_a", "tarefa_a", "resultado_a")
        self.hub.store_episode("agente_b", "tarefa_b", "resultado_b")
        ctx = self.hub.get_context("agente_a", n=10)
        self.assertIn("tarefa_a", ctx)
        self.assertNotIn("tarefa_b", ctx)

    def test_get_context_respects_n(self):
        """get_context deve respeitar o limite n."""
        for i in range(20):
            self.hub.store_chat("user", f"msg {i}")
        ctx = self.hub.get_context("test", n=5)
        # Contar ocorrências de "[user]"
        count = ctx.count("[user]")
        self.assertLessEqual(count, 5)

    def test_singleton(self):
        """MemoryHub deve ser singleton."""
        hub2 = MemoryHub()
        self.assertIs(self.hub, hub2)

    def test_persistence(self):
        """Dados devem persistir entre instâncias."""
        self.hub.store_chat("user", "persistir")
        # Recarregar
        hub2 = MemoryHub()
        hub2.filepath = self.hub.filepath
        entries = hub2._load_all()
        chats = [e for e in entries if e.get("type") == "chat"]
        self.assertGreater(len(chats), 0)

    def test_clear(self):
        """clear deve limpar todos os dados."""
        self.hub.store_chat("user", "dado")
        self.hub.clear()
        entries = self.hub._load_all()
        self.assertEqual(len(entries), 0)

    def test_store_chat_with_timestamp(self):
        """store_chat deve adicionar timestamp."""
        self.hub.store_chat("user", "com tempo")
        entries = self.hub._load_all()
        chat = entries[-1]
        self.assertIn("timestamp", chat)
        self.assertIn("T", chat["timestamp"])  # ISO format

    def test_store_episode_with_timestamp(self):
        """store_episode deve adicionar timestamp."""
        self.hub.store_episode("agente", "tarefa", "resultado")
        entries = self.hub._load_all()
        ep = entries[-1]
        self.assertIn("timestamp", ep)


if __name__ == "__main__":
    unittest.main()
