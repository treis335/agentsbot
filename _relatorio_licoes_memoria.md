# Relatório de Análise da Memória Episódica — Lições Aprendidas

**Data:** 2026-05-30  
**Agente:** Supervisor  
**Fonte:** main.log (125.784 linhas), wakeup_v3.log (5.622 linhas), backlog.json, hub.jsonl, debug files

---

## Sumário Executivo

O ecossistema Correoto executou **125.784 operações** registadas em log. Foram identificados **3 problemas críticos**, **4 padrões de ineficiência** e **6 lições acionáveis** para melhorar futuras execuções.

---

## 🔴 Problemas Críticos Detectados

### 1. Loop Infinito de Reinicializações (CRÍTICO)
- **1587** erros `Conflict: terminated by other getUpdates request` — múltiplas instâncias do bot Telegram a competir
- **150 resets** forçados no wakeup_v3 + **940** deteções de "main.py não está a correr"
- Causa raiz: O wakeup reinicia o main.py, mas o main.py demora a iniciar ou morre rapidamente, criando um ciclo vicioso
- **Lição #1:** Implementar **lock de processo** real (ficheiro .lock com PID) e verificar se o processo já existe antes de reiniciar

### 2. Memória Episódica Virtualmente Vazia (CRÍTICO)
- Apenas **1 episódio** registado no `hub.jsonl` (do agente `log_diagnostic`)
- **0 lições** armazenadas no sistema de memória
- A tarefa "Analisa a memória episódica" foi executada **27 vezes** sem nunca realmente **povoar** a memória com episódios
- **Lição #2:** A tarefa de análise só faz sentido depois de existirem episódios para analisar. **Prioridade:** implementar `store_episode()` em cada execução de agente.

### 3. Corrupção da GlobalMemory (ALTO)
- **9 erros** de `GlobalMemory: Erro ao carregar` — JSON corrompido, encoding inválido
- Causa: escrita concorrente ou falha de encoding UTF-8 vs cp1252 no Windows
- **Lição #3:** Adicionar **validação de integridade** antes de escrever (try/except + backup automático + atomic write)

---

## 🟡 Padrões de Ineficiência

### 4. Duplicação Maciça de Tarefas no Backlog
- **128 tarefas** no backlog, mas apenas **18 títulos únicos**
- Tarefa "Analisa a memória episódica" aparece **27 vezes** como "completed"
- Tarefa "Cria um novo agente" aparece **21 vezes**
- **Lição #4:** Implementar **deduplicação automática** no backlog — verificar se tarefa similar já existe antes de adicionar

### 5. Agentes sem Registo de Episódios
- Supervisor executou **24 vezes** mas **0 episódios** registados
- Outros agentes (developer, auto_fixer, etc.) também sem registo
- O sistema tem o método `store_episode()` implementado mas **nunca é chamado**
- **Lição #5:** Cada execução de agente deve terminar com `store_episode()` — tornar isto **obrigatório** no ciclo de vida

### 6. Erros de Unicode no Windows
- **6 erros** `UnicodeEncodeError` com emojis (🔧, ✅, ❌)
- O Windows usa cp1252 que não suporta emojis
- **Lição #6:** Usar **encoding forçado utf-8** em todos os prints/logs, ou substituir emojis por texto ASCII `[OK]`, `[FAIL]`, `[INFO]`

---

## ✅ Recomendações Prioritárias

| # | Ação | Impacto | Esforço |
|---|------|---------|---------|
| 1 | Adicionar `store_episode()` no final de cada execução de agente | Alto — memória começa a ser povoada | Baixo |
| 2 | Implementar lock de processo com PID para evitar múltiplas instâncias | Alto — elimina loop de reinicializações | Médio |
| 3 | Adicionar atomic write + backup na GlobalMemory | Alto — elimina corrupção de dados | Baixo |
| 4 | Deduplicar backlog antes de adicionar tarefas | Médio — reduz ruído e repetição | Baixo |
| 5 | Substituir emojis por texto ASCII nos logs | Médio — compatibilidade Windows | Baixo |
| 6 | Criar rota de manutenção periódica da memória (compressão, cleanup) | Médio — saúde a longo prazo | Médio |

---

## Métricas Pós-Implementação (Target)

| Métrica | Atual | Target |
|---------|-------|--------|
| Episódios no hub.jsonl | 1 | >50 |
| Lições armazenadas | 0 | >20 |
| Erros Conflict Telegram/dia | 1587 | <10 |
| Erros GlobalMemory/dia | 9 | 0 |
| Tarefas duplicadas no backlog | 110/128 (86%) | <10% |
| Taxa de sucesso do supervisor | ~96% | >99% |

---

## Conclusão

O ecossistema tem **código sólido** (métodos `store_episode()`, `get_lessons()`, `MemoryHub` implementados) mas **nunca são usados** no fluxo real. O problema não é técnico — é de **orquestração**: os agentes executam tarefas mas não registam o que aprenderam.

**Ação imediata recomendada:** Modificar o `AgentExecutor` para chamar `store_episode()` automaticamente no final de cada execução, com `success`, `result` e `lesson` preenchidos.
