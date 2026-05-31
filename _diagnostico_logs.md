# Diagnóstico de Logs — 2026-05-31 02:21

## Resumo Executivo

3 problemas críticos identificados nos logs. 1 correção implementada (a mais simples e de maior impacto).

---

## Problema 1: Backlog Inchado com Tarefas Repetidas 🔴 CRÍTICO

**Sintoma:** 229 tarefas no backlog, 190 eram duplicatas exatas. 3 tarefas "running" presas há dias.

**Causa Raiz:** O sistema autónomo gerava as mesmas tarefas de fallback repetidamente quando o ciclo de debate falhava. Cada execução adicionava uma nova cópia em vez de verificar se já existia.

**Evidência nos Logs:**
- `auto_24f26643` — "Analisa os logs..." (37x duplicada)
- `auto_fcc3cba3` — "Analisa a memória episódica..." (43x duplicada)
- 3 tarefas "running" desde data anterior a 2026-05-31

**Correção Implementada: ✅**
- 190 duplicatas removidas
- 3 tarefas "running" presas → marcadas como "failed"
- Backlog reduzido de **229 → 39 tarefas**
- 0 tarefas pendentes/failed/running atualmente

---

## Problema 2: Supervisor Crash por UnicodeEncodeError 🟡 MÉDIO

**Sintoma:** `supervisor.log` mostra crash com `'charmap' codec can't encode character '\U0001f680'`

**Causa Raiz:** O Windows usa codificação cp1252 que não suporta emojis/unicode. O `supervisor_ultra.py` tentava fazer `print()` de emojis (🚀, 🔧, etc.) sem sanitização.

**Evidência nos Logs:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'
Fatal Python error: _enter_buffered_busy: could not acquire lock
```

**Estado:** O ficheiro `supervisor_ultra.py` já foi removido. O `autonomous_loop.py` já tem função `log_cycle()` com proteção Unicode em 3 níveis:
1. Sanitização UTF-8 com `errors='replace'`
2. Fallback para ASCII puro
3. Fallback final para log básico

**Correção: ✅ JÁ IMPLEMENTADA (por execuções anteriores)**

---

## Problema 3: Bytecode .pyc Desatualizado 🟢 BAIXO

**Sintoma:** `main_stderr.log` mostra: `[Telegram] Erro ao inicializar: unterminated f-string literal (detected at line 460)`

**Causa Raiz:** O ficheiro `bot/handlers.py` tem 455 linhas (source atual), mas o bytecode compilado (`handlers.cpython-313.pyc`) referia uma linha 460 de uma versão anterior.

**Estado Atual:**
- 1 ficheiro .pyc encontrado
- Bytecode está atualizado (source não é mais recente)
- O erro "line 460" era de uma versão anterior do código
- **Não requer ação** neste momento

**Recomendação:** Adicionar limpeza automática de `.pyc` no startup para evitar dessincronia.

---

## Métricas

| Métrica | Antes | Depois |
|---------|-------|--------|
| Tarefas no backlog | 229 | 39 ✅ |
| Tarefas duplicadas | 190 | 0 ✅ |
| Tarefas "running" presas | 3 | 0 ✅ |
| Ficheiros lock | 0 | 0 ✅ |
| Bytecode desatualizado | 0 | 0 ✅ |
| Proteção Unicode | Parcial | 3 níveis ✅ |

---

## Recomendações

1. **[MÉDIA]** Adicionar verificação de duplicatas no `add_to_backlog()` do autonomous_loop.py
2. **[BAIXA]** Limpar cache `.pyc` automaticamente no startup (`find . -name "*.pyc" -delete`)
3. **[BAIXA]** Centralizar logging num módulo `core/safe_logger.py` para todo o ecossistema
