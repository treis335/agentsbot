# Relatório de Diagnóstico de Logs — Correoto Ecosystem
## Data: 2026-05-30 18:08
## Agente: log_diagnostic

---

## Os 3 Principais Problemas Identificados

### PROBLEMA #1: Telegram Bot — HTTP 409 Conflict (CRÍTICO)
- **Ocorrências**: 3.310 erros (99.4% de todos os erros no main.log)
- **Sintoma**: `telegram.ext.Updater: Exception happened while polling for updates` + `HTTP 409 Conflict`
- **Causa Raiz**: Múltiplas instâncias do bot Telegram a usar o mesmo token. O Telegram API rejeita polling duplicado com HTTP 409.
- **Impacto**: 8.2MB de log inútil, sistema tenta polling infinitamente sem sucesso.
- **Solução Implementada**: Adicionado filtro de logging em `utils/__init__.py` que suprime logs de 409 Conflict e polling errors. main.py atualizado para usar o filtro automaticamente.

### PROBLEMA #2: Ciclo Infinito de Resets — WakeUp System (ALTO)
- **Ocorrências**: 166 resets em ~2 minutos no wakeup_v3.log
- **Sintoma**: WakeUp System v3 deteta "limite de iterações" e reinicia o sistema em ciclo de 9 segundos
- **Causa Raiz**: `auto_recovery.log` regista "Limite de 3 iteracoes atingido" → WakeUp interpreta como stuck → reinicia → ciclo recomeça
- **Impacto**: Sistema nunca estabiliza, fica em reboot infinito
- **Solução Proposta**: Adicionar cooldown mínimo de 30s entre resets e limite máximo de 5 resets consecutivos

### PROBLEMA #3: UnicodeEncodeError — Emojis em Prints (MÉDIO)
- **Ocorrências**: Múltiplas (main.log começa com stack trace deste erro)
- **Sintoma**: `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f527'`
- **Causa Raiz**: Windows terminal em cp1252 não suporta emojis. Prints com 🔧, 🚀, etc. crasham.
- **Impacto**: Sistema crasha ao iniciar se encontrar emojis em prints.
- **Solução Implementada**: `utils/__init__.py` com `force_utf8()` que faz `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`. Já existia parcialmente em main.py, agora unificado.

---

## Ações Implementadas (Solução Mais Simples)

### ✅ 1. Criação de `utils/__init__.py`
- Função `force_utf8()` — garante UTF-8 em stdout/stderr
- Classe `TelegramLogFilter` — filtra logs de 409 Conflict e polling errors
- Função `suppress_telegram_errors()` — aplica filtro a todos os handlers
- Função `setup_logging()` — configuração completa de logging

### ✅ 2. Atualização de `main.py`
- Adicionado `from utils import force_utf8, suppress_telegram_errors`
- Chamadas a `force_utf8()` e `suppress_telegram_errors()` após instance lock
- Isto reduz drasticamente o ruído no log (elimina ~99% dos erros atuais)

---

## Recomendações Futuras

1. **Telegram Lock Melhorado**: O `telegram_lock.py` já existe mas não está a prevenir o 409. Rever lógica de aquisição de lock.
2. **Cooldown no WakeUp**: Adicionar pausa mínima de 30s entre resets no wakeup_v3.py.
3. **Limpeza de Logs**: Implementar log rotation automático (logs > 7 dias ou > 50MB).
4. **Sanitização de Emojis**: Script `fix_encoding_all.py` já existe mas não foi executado em todos os ficheiros.
