# 🧠 DESAFIOS LANÇADOS À EQUIPA CORREOTO

## 🎯 Missão Geral
Transformar o Correoto num **Verdadeiro LLM Autónomo** com raciocínio profundo, memória viva e auto-aprendizagem.

---

## 📋 DESAFIO 1 — ARQUITETO + DEVELOPER
### 🏗️ "Motor de Raciocínio Profundo (Deep Reasoning Engine)"

**Problema:** O sistema atual responde a comandos mas não "pensa" antes de agir.

**Tarefa:** Criar `core/reasoning_engine.py` que implemente:
- Chain-of-Thought multi-passo (raciocínio passo a passo)
- Auto-verificação de cada passo
- Fallback quando o raciocínio falha
- Logging de todo o processo de pensamento

**Especificação:**
```python
class ReasoningEngine:
    def reason(self, task: str, context: dict) -> ReasoningChain:
        """
        1. Decompor tarefa em sub-passos
        2. Para cada passo: pensar → verificar → validar
        3. Se passo falha: tentar abordagem alternativa
        4. Retornar cadeia completa de raciocínio
        """
```

**Métrica de sucesso:** O sistema explica COMO chegou a uma decisão.

---

## 📋 DESAFIO 2 — AUTO-EVOLVER + AUTO-FIXER
### 🔧 "Sistema Imunológico Auto-Reparável"

**Problema:** Quando o sistema crasha, ninguém repara automaticamente.

**Tarefa:** Criar `core/auto_healer.py` que:
- Monitoriza logs de erro em tempo real
- Detecta padrões de falha (ex: "RPC timeout", "import error")
- Tem uma base de "receitas" para erros conhecidos
- Executa ações corretivas automaticamente
- Se não sabe resolver, cria um relatório detalhado

**Exemplo de receita:**
```json
{
  "pattern": "ModuleNotFoundError: No module named 'X'",
  "action": "run_shell('pip install X')",
  "verify": "run_python('import X')"
}
```

**Métrica de sucesso:** 90% dos erros comuns são resolvidos em <30s.

---

## 📋 DESAFIO 3 — GESTOR DE MEMÓRIA
### 🧠 "Memória Viva com RAG Interno"

**Problema:** A memória atual é apenas armazenamento passivo.

**Tarefa:** Evoluir `memory/` para um sistema RAG (Retrieval-Augmented Generation):
- Indexar todas as memórias por embeddings (usar sentence-transformers ou similar)
- Criar `memory/rag_engine.py` com:
  - `store(memory)` → guarda + indexa
  - `retrieve(query, top_k=5)` → busca por similaridade semântica
  - `compress(old_memories)` → sumariza memórias antigas
  - `forget(below_priority=0.3)` → "esquece" o que não é importante

**Métrica de sucesso:** O sistema recupera a memória relevante em <100ms.

---

## 📋 DESAFIO 4 — QA TESTER
### 🧪 "Testes Automáticos com Auto-Geração"

**Problema:** O sistema não tem testes automatizados.

**Tarefa:** Criar `tests/` com:
- `tests/test_reasoning.py` — testes para o motor de raciocínio
- `tests/test_memory.py` — testes para a memória
- `tests/test_auto_healer.py` — testes para o auto-reparador
- `tests/test_integration.py` — testes de integração
- Gerador automático de testes: `tools/test_generator.py`

**Métrica de sucesso:** Cobertura de testes > 70%.

---

## 📋 DESAFIO 5 — TODOS OS AGENTES
### 🌐 "Autonomia Total — O Sistema que se Auto-Gere"

**Problema:** O sistema ainda precisa de comandos do utilizador.

**Tarefa:** Implementar `core/autonomous_orchestrator.py` que:
- Define objetivos semanais automaticamente
- Decompõe objetivos em tarefas para cada agente
- Monitoriza o progresso
- Ajusta prioridades com base em resultados
- Gera relatórios de evolução

**Ciclo Autónomo:**
```
1. [Domingo] Definir objetivos da semana
2. [Diário] Atribuir tarefas aos agentes
3. [Hora a hora] Verificar progresso
4. [Se bloqueado] Replanear ou pedir ajuda
5. [Sábado] Gerar relatório semanal
```

**Métrica de sucesso:** O sistema opera 24/7 sem intervenção humana.

---

## 📋 DESAFIO 6 — DEVOPS
### 🚀 "Deploy Automático com Auto-Escala"

**Problema:** O sistema só corre localmente.

**Tarefa:** Criar `devops/` com:
- `Dockerfile` — containerização do sistema
- `docker-compose.yml` — orquestração multi-serviço
- `deploy.sh` — script de deploy automático
- `monitoring.sh` — monitorização de saúde
- `backup.sh` — backup automático da memória

**Métrica de sucesso:** `docker-compose up -d` lança o sistema completo.

---

## 📋 DESAFIO 7 — DOCUMENTADOR
### 📚 "Documentação Auto-Consciente"

**Problema:** O sistema não documenta o que aprende.

**Tarefa:** Criar `tools/auto_documenter.py` que:
- Analisa o código e gera documentação automática
- Mantém um "diário de bordo" do sistema
- Gera relatórios de evolução semanais
- Cria tutoriais interativos baseados no uso real

**Métrica de sucesso:** Cada módulo tem documentação gerada automaticamente.

---

## 🏆 DESAFIO EXTRA — COMPETIÇÃO INTERNA
### ⚔️ "Qual agente evolui mais em 24h?"

**Regras:**
1. Cada agente escolhe 1 desafio dos acima
2. Implementa e testa
3. No final do dia, apresentam resultados
4. O vencedor ganha prioridade nos recursos do sistema

**Prémio:** O agente vencedor decide o próximo foco do sistema.

---

## 📊 ESTADO ATUAL DO SISTEMA

| Componente | Estado | Prioridade |
|------------|--------|------------|
| Motor de Raciocínio | ❌ Não existe | 🔴 CRÍTICA |
| Auto-Reparação | ❌ Não existe | 🔴 CRÍTICA |
| RAG Interno | ❌ Não existe | 🟡 ALTA |
| Testes Automatizados | ❌ Não existe | 🟡 ALTA |
| Orquestrador Autónomo | ❌ Não existe | 🟢 MÉDIA |
| Deploy Automático | ❌ Não existe | 🟢 MÉDIA |
| Documentação Auto | ❌ Não existe | 🔵 BAIXA |

---

## 🚀 PRÓXIMOS PASSOS IMEDIATOS

1. **Agora:** Criar `core/reasoning_engine.py` (Arquiteto + Developer)
2. **Em paralelo:** Criar `core/auto_healer.py` (Auto-Evolver + Auto-Fixer)
3. **Sequencial:** Criar `memory/rag_engine.py` (Gestor de Memória)
4. **Quando pronto:** Testar tudo (QA Tester)
5. **Final:** Orquestrador Autónomo + Deploy

---

*Gerado pelo Supervisor Principal | Projeto: Correoto | Data: 2026-05-26*
