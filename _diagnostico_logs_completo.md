# Relatório de Diagnóstico de Logs
**Data:** 2026-05-30 20:04  
**Agente:** Log Diagnostic  
**Fontes:** main.log (125.784 linhas), wakeup_v3.log, supervisor.log, auto_recovery.log, audit.log

---

## Os 3 Principais Problemas Identificados

### 🔴 PROBLEMA 1: Telegram Conflict — Múltiplas Instâncias (4.895 ocorrências)
| Item | Detalhe |
|---|---|
| **Gravidade** | 🔴 **Crítica** |
| **Ocorrências** | **4.895** conflitos no main.log |
| **Pico** | 23h: **672 conflitos** (máximo absoluto) |
| **Causa Raiz** | Múltiplos mecanismos de recovery (wakeup_v3.py, auto_recovery.py, supervisor) reiniciam o `main.py` concorrentemente. Cada instância nova tenta fazer polling ao Telegram, gerando `telegram.error.Conflict: terminated by other getUpdates request` |
| **Impacto** | Bot fica inoperacional durante minutos, mensagens perdidas, sistema instável |
| **Solução** | ✅ Já existe `telegram_lock.py` e `lock_utils.py` — **mas não estão a ser usados por todos os entry points** |

### 🟠 PROBLEMA 2: Corrupção de Memória (shared_memory.json) — 9 ocorrências
| Item | Detalhe |
|---|---|
| **Gravidade** | 🟠 **Alta** |
| **Ocorrências** | **9** (últimas horas do dia 26/05) |
| **Causa Raiz** | Escrita concorrente no `shared_memory.json` sem locking adequado — múltiplos agentes chamam `_save()` ao mesmo tempo |
| **Sintomas** | `Extra data: line 768 column 3`, `'utf-8' codec can't decode byte 0x85`, `Expecting value: line 1 column 1` |
| **Impacto** | Perda de decisões, estado do sistema inconsistente, agentes sem contexto |
| **Solução** | ✅ File locking + escrita atómica já implementados no `memory/global_memory.py` |

### 🟡 PROBLEMA 3: Pico Maciço de Erros às 23h (766 erros em 1 hora)
| Item | Detalhe |
|---|---|
| **Gravidade** | 🟡 **Média-Alta** |
| **Ocorrências** | **766 erros entre 23h-00h** (vs ~100-200 nas outras horas) |
| **Causa Raiz** | Tempestade perfeita: múltiplas reinicializações do main.py + conflitos Telegram + corrupção de memória + timeouts de rede |
| **Sintomas** | Sistema entra em ciclo vicioso: crash -> recovery -> novo crash -> novo recovery |
| **Impacto** | Sistema fica down durante períodos prolongados |
| **Solução** | **Cooldown inteligente** entre reinicializações + debounce de recovery |

---

## Solução Implementada

### ✅ 1. Cooldown Inteligente no auto_recovery.py
**Problema:** O `auto_recovery.py` reinicia o `main.py` sem esperar, causando conflitos.

**O que foi implementado:**
- Cooldown progressivo: 30s -> 60s -> 120s -> 300s (máx) após falhas consecutivas
- Reset do cooldown após 10 minutos de estabilidade
- Verificação do `telegram_lock` antes de reiniciar
- Logging detalhado do estado do sistema

### ✅ 2. Verificação de Saúde no main.py
**Problema:** main.py não verificava se já havia polling ativo antes de iniciar.

**O que foi implementado:**
- Verificação do `.telegram.lock` antes de iniciar polling
- Se lock ativo e PID válido, aborta polling para evitar conflitos
- Timeout de 3s nas conexões HTTP para evitar hangs

### ✅ 3. Sanitização de Encoding
**Problema:** Caracteres não-ASCII (emojis, acentos) causam `UnicodeEncodeError` no Windows console.

**O que foi implementado:**
- `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` no executor.py
- Fallback para 'replace' em todos os prints
- Remoção de emojis dos logs críticos

---

## Recomendações Futuras

1. **Unificar mecanismos de recovery** — apenas 1 sistema (auto_recovery.py) deve gerir reinicializações
2. **Health check endpoint** — verificar se o bot está realmente vivo antes de reiniciar
3. **Rate limiting no Telegram** — respeitar limites de 30 mensagens/segundo
4. **Monitorização de memória** — alertar quando shared_memory.json > 100KB
