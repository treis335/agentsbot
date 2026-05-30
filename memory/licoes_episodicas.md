# Lições Extraídas da Memória Episódica

**Data:** 2026-05-30 16:49
**Agente:** gestor_memoria
**Fonte:** loop_episodes.json (200 episódios), episódica/ (101 episódios), event_logs (52 eventos), conversation.jsonl (12 msgs)

---

## 🔴 LIÇÃO 1: Loops de repetição matam a produtividade
**Problema:** 139/200 episódios (69.5%) são a mesma tarefa `task_unify_memory_systems` executada pelo qa_tester. Destes, 30 resultaram em "tarefa não executada" e 14 em "write_file não funcionou".
**Causa raiz:** O sistema não detecta que uma tarefa está a falhar repetidamente e continua a reatribuí-la ao mesmo agente.
**Acção:** Implementar `max_retries` por tarefa (ex: 3 tentativas máx). Após 3 falhas consecutivas, arquivar a tarefa e notificar o supervisor.

---

## 🔴 LIÇÃO 2: Sistema de lições não é usado
**Problema:** 0% dos 200 episódios têm o campo `lesson` preenchido. O `lesson_extractor.py` existe mas nunca é chamado pelo loop.
**Causa raiz:** O pipeline do ciclo autónomo não integra a extracção de lições após cada tarefa.
**Acção:** Integrar `lesson_extractor.py` no fim de cada execução de tarefa. Cada episódio deve ter `lesson` obrigatória.

---

## 🔴 LIÇÃO 3: MemoryHub (hub.jsonl) está vazio
**Problema:** O ficheiro `memory/hub.jsonl` tem 0 linhas. O código `core/memory_hub.py` existe (487 linhas) mas nunca foi populado.
**Causa raiz:** O `MemoryHub` foi criado mas nunca integrado no pipeline de execução dos agentes.
**Acção:** Forçar a migração: cada `write` de episódio deve ir para o hub.jsonl. Remover sistemas duplicados.

---

## 🟡 LIÇÃO 4: Supervisor gera ruído repetitivo
**Problema:** O supervisor enviou 12 mensagens quase idênticas ("AutonomousLoop inicializado. Pronto para trabalhar.") para a conversation.jsonl.
**Causa raiz:** Cada reinício do ciclo gera a mesma mensagem sem verificar se já foi enviada antes.
**Acção:** Implementar deduplicação de mensagens no supervisor. Se a mensagem for idêntica à anterior, não repetir.

---

## 🟡 LIÇÃO 5: Ciclo autónomo entra em loop
**Problema:** 2 loops detetados em apenas 7 ciclos (28.5% de taxa de loop). O ciclo ficou preso na fase "pensar".
**Causa raiz:** O sistema não tem um mecanismo de "escape" quando detecta que está a repetir a mesma acção.
**Acção:** Quando identical_action_count > 3, forçar mudança de fase ou pausa de 60s.

---

## 🟢 LIÇÃO 6: Supervisor tem boa taxa de sucesso em acções variadas
**Oportunidade:** O supervisor executou 100 episódios com 96% de sucesso, usando 5 tipos de ferramentas diferentes (run_shell, read_file, write_file, task_complete, list_files).
**Acção:** Usar o supervisor como referência de boas práticas. Documentar o seu padrão de execução para outros agentes.

---

## 🟢 LIÇÃO 7: Event logs estão estruturados mas subutilizados
**Oportunidade:** Os event_logs têm 52 eventos estruturados com IDs, timestamps e metadados. Podem ser usados para debugging e análise de tendências.
**Acção:** Criar um índice de eventos por tipo e agente. Usar para detectar padrões de falha antes que se tornem loops.

---

## 🟢 LIÇÃO 8: write_file precisa de validação prévia
**Problema:** 16 episódios reportam falha da ferramenta `write_file`. O qa_tester tentou repetidamente sem sucesso.
**Causa raiz:** O agente não verificou se o content estava vazio antes de chamar write_file.
**Acção:** Adicionar validação: antes de write_file, verificar se content tem > 0 caracteres. Se estiver vazio, abortar e reportar.

---

## 📊 Métricas Consolidadas

| Métrica | Valor |
|---|---|
| Total episódios analisados | 200 |
| Episódios com lição | 0 (0%) |
| Tarefas únicas | ~12 |
| Tarefa mais repetida | task_unify_memory_systems (139x) |
| Agente mais activo | qa_tester (139 eps) |
| Taxa de sucesso (supervisor) | 96% |
| Falhas de write_file | 16 |
| Loops no ciclo | 2 em 7 ciclos |
| hub.jsonl populado | 0 linhas |
| Eventos nos logs | 52 |

---

## ✅ Checklist de Acções Prioritárias

- [ ] 1. Implementar `max_retries=3` para evitar loops de tarefa
- [ ] 2. Integrar `lesson_extractor.py` no pipeline do ciclo
- [ ] 3. Forçar escrita no `hub.jsonl` em cada episódio
- [ ] 4. Deduplicar mensagens do supervisor
- [ ] 5. Adicionar escape de loop no ciclo autónomo
- [ ] 6. Validar content antes de write_file
- [ ] 7. Indexar event_logs por tipo para debugging rápido
