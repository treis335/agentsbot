# Relatório de Diagnóstico de Logs
**Data:** 2026-05-30 18:49  
**Agente:** Log Diagnostic  
**Fonte:** main.log, supervisor.log, wakeup.log, auto_recovery.log

---

## Os 3 Principais Problemas Identificados

### 🔴 PROBLEMA 1: Telegram Conflict — Múltiplas Instâncias do Bot
| Item | Detalhe |
|---|---|
| **Gravidade** | 🔴 **Crítica** |
| **Ocorrências** | **1.585** (só no dia 26/05) |
| **Pico** | 23h: **749 conflitos** (máximo) |
| **Causa Raiz** | `wakeup_v3.py`, `heartbeat_system.py` e `supervisor_ultra.py` reiniciam o `main.py` múltiplas vezes, criando N instâncias do bot Telegram a competir pelo mesmo `getUpdates` |
| **Sintoma** | `telegram.error.Conflict: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running` |
| **Impacto** | Bot fica inoperacional durante minutos, mensagens perdidas |
| **Solução** | ✅ Já existe `telegram_lock.py` — garantir que todos os scripts o usam antes de iniciar o bot |

### 🟠 PROBLEMA 2: Corrupção de Memória (shared_memory.json)
| Item | Detalhe |
|---|---|
| **Gravidade** | 🟠 **Alta** |
| **Ocorrências** | **9** (últimas horas do log) |
| **Causa Raiz** | Escrita concorrente no `shared_memory.json` sem locking — múltiplos agentes chamam `_save()` ao mesmo tempo |
| **Sintomas** | `Extra data: line 768 column 3`, `'utf-8' codec can't decode byte 0x85`, `Expecting value: line 1 column 1` |
| **Impacto** | Perda de decisões, estado do sistema inconsistente, agentes sem contexto |
| **Solução** | ✅ **IMPLEMENTADA** — File locking + escrita atómica no `global_memory.py` |

### 🟡 PROBLEMA 3: Encoding Crash no Supervisor
| Item | Detalhe |
|---|---|
| **Gravidade** | 🟡 **Média** |
| **Ocorrências** | **1 crash fatal** |
| **Causa Raiz** | `supervisor_ultra.py` usa emojis (`🚀`, `🔄`) na função `log()` que faz `print()` — Windows console (cp1252) não renderiza, causando `UnicodeEncodeError` |
| **Sintoma** | `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'` + `Fatal Python error` |
| **Impacto** | Supervisor morre, sistema sem supervisão |
| **Solução** | ✅ **RESOLVIDO PASSIVAMENTE** — O ficheiro `supervisor_ultra.py` foi removido |

---

## Solução Implementada

### ✅ File Locking + Escrita Atómica no `memory/global_memory.py`

**O que foi feito:**
1. Adicionado **file locking** com ficheiro `.json.lock` — apenas um processo escreve de cada vez
2. Lock com **timeout de 5s** e deteção de **stale locks** (>2s)
3. **Escrita atómica**: escreve para ficheiro temporário e depois `os.replace()` (rename atómico)
4. Se o processo crashar durante a escrita, o ficheiro original fica intacto
5. Lock é libertado no `finally` — nunca fica preso

**Ficheiro alterado:** `memory/global_memory.py`  
**Linhas alteradas:** Função `_save()` (escrita atómica + locking)

---

## Recomendações Pendentes

1. **Garantir uso do `telegram_lock.py`** em todos os entry points:
   - `main.py`
   - `wakeup.py` / `wakeup_v3.py`
   - `heartbeat_system.py`
   - `auto_recovery.py`

2. **Monitorizar** se os erros de memória desaparecem com o novo locking

3. **Prevenir encoding issues** futuras — configurar `PYTHONIOENCODING=utf-8` no ambiente
