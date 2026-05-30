# LICOES APRENDIDAS DA MEMORIA EPISODICA
# Gerado por gestor_memoria em 2026-05-30 14:05

## LICAO 1: UnicodeEncodeError no Windows (cp1252) - CRITICO
**Problema:** Emojis em prints de ficheiros .py causam crash total no Windows
**Ficheiros afetados:** tools/fs_tools.py, tools/web_tools.py, auto_evolve.py, auto_evolve_loop.py, auto_update.py, supervisor_ultra.py
**Impacto:** 6 crashes que impediram o sistema de iniciar, levando a 140 resets
**Solucao:** Remover emojis de todos os prints. Usar texto ASCII simples.
**Status:** JA CORRIGIDO (commit 4c3011f)
**Regra:** NUNCA usar emojis em prints de ficheiros que correm no Windows

## LICAO 2: Loop Infinito de Resets - CRITICO
**Problema:** WakeUp system detetava 'stuck' e reiniciava main.py repetidamente (140x)
**Causa:** O erro de Unicode impedia o main.py de iniciar, wakeup interpretava como 'stuck'
**Impacto:** ~7 minutos de loop, logs inchados para 8.2MB
**Solucao:** Implementar backoff exponencial (esperar mais a cada reset), maximo de N resets antes de alertar humano
**Regra:** Sistema de recovery precisa de detetar se o erro e o mesmo da tentativa anterior

## LICAO 3: Telegram Conflict - ALTO
**Problema:** 'Conflict: terminated by other getUpdates request'
**Causa:** Duas instancias do bot Telegram a correr em simultaneo
**Impacto:** Bot para de responder
**Solucao:** Usar lock file (.correoto.lock) para impedir segunda instancia. Verificar processo antes de iniciar.
**Status:** Lock file existe mas nao e verificado antes de iniciar

## LICAO 4: Heartbeat Parou - MEDIO
**Problema:** heartbeat.flg parou em 2026-05-26, sistema ficou sem batimento cardiaco
**Impacto:** Nao havia monitorizacao de saude ativa
**Solucao:** Heartbeat deve ser watchdog independente com alerta se parar

## LICAO 5: smart_pace com iteration_count=0 - MEDIO
**Problema:** smart_pace.flg mostra iteration_count=0 apesar de 140 resets
**Causa:** Os resets reiniciavam o contador antes de incrementar
**Solucao:** Persistir contagem de iteracoes num ficheiro separado, nao em memoria

## LICAO 6: agents.json vs agents.json.bak - BAIXO
**Problema:** agents.json (1.5KB, 17 agentes) vs agents.json.bak (27KB, agentes com detalhes)
**Causa:** agents.json foi simplificado perdendo informacao de agentes anteriores
**Solucao:** Manter schema unico. Se ha backup com mais dados, consolidar.

## LICAO 7: MemoryHub Existe mas Nao e Usado - MEDIO
**Problema:** MemoryHub (hub.jsonl) implementado mas sistema continua a usar memory/ antigo
**Causa:** Compatibilidade mantida mas migracao nao forcada
**Solucao:** Forcar migracao para MemoryHub como unico ponto de verdade

## RECOMENDACOES PRIORITARIAS:
1. [CRITICO] Validar que nenhum ficheiro .py tem emojis (pre-commit hook)
2. [CRITICO] Adicionar backoff exponencial ao wakeup system
3. [ALTO] Verificar lock file antes de iniciar bot Telegram
4. [ALTO] Implementar watchdog para heartbeat
5. [MEDIO] Consolidar agents.json com dados do backup
6. [MEDIO] Forcar migracao para MemoryHub