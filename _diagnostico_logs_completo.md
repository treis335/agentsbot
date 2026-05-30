# Diagnóstico de Logs — Correoto Ecosystem

**Data:** 2026-05-30 17:15  
**Agente:** log_diagnostic  
**Estado atual:** Sistema ONLINE (API responde em localhost:8080)

---

## OS 3 PRINCIPAIS PROBLEMAS

### 🥇 PROBLEMA #1 — Erro crítico: ficheiro `handlers.py` com sintaxe inválida (GRAVIDADE: ALTA)

**Evidência:** `main_stderr.log`, `run_stderr.log`, `startup.log` — todas as execuções mostram:
```
[ERROR] correoto: [Telegram] Erro ao inicializar: unterminated f-string literal (detected at line 460) (handlers.py, line 460)
```

**Impacto:** O bot Telegram **NÃO INICIA**. O sistema funciona apenas via API REST. O utilizador não pode interagir via Telegram.

**Causa raiz:** Ficheiro `bot/handlers.py` contém uma f-string mal formatada (`f"..."` sem fechar) na linha 460.

**Estado atual:** Já foi corrigido (compila sem erros agora), mas o sistema continua a não usar Telegram porque o erro bloqueou o startup.

---

### 🥈 PROBLEMA #2 — 79.8% de erro em `write_file` (GRAVIDADE: ALTA)

**Evidência:** Métricas da API mostram:
| Tool | Calls | Erros | % Erro |
|------|-------|-------|--------|
| write_file | 475 | 379 | **79.8%** |
| read_file | 344 | 1 | 0.3% |
| run_python | 46 | 3 | 6.5% |
| run_shell | 300 | 0 | 0% |

**Impacto:** Quase 4 em cada 5 tentativas de escrever ficheiros falham. Isto degrada severamente a capacidade do sistema de guardar resultados, memória, e relatórios.

**Causa raiz provável:** Permissões de escrita em certos diretórios, ou conflitos de concorrência (múltiplos agentes a escrever no mesmo ficheiro simultaneamente).

---

### 🥉 PROBLEMA #3 — Ciclo infinito de reinicialização (wakeup loop) (GRAVIDADE: MÉDIA)

**Evidência:** `wakeup_v3.log` mostra **8+ reinicializações** em menos de 2 minutos:
```
[06:45:52] REINICIANDO... (reset #1)
[06:46:01] REINICIANDO... (reset #2)
[06:46:10] REINICIANDO... (reset #3)
...até reset #8+
```

**Impacto:** O sistema entra em ciclo de restart infinito porque:
1. `main.py` crasha com UnicodeEncodeError (emoji no print)
2. `wakeup_v3.py` detecta "stuck" e reinicia
3. `main.py` crasha novamente
4. Repete ad infinitum

**Causa raiz:** O `print()` com emojis no `fs_tools.py` (linha 29) crasha no Windows CP1252. Já foi corrigido com `sys.stdout.reconfigure(encoding="utf-8")`, mas o log mostra que o crash acontecia **antes** do reconfigure ser executado.

---

## SOLUÇÕES PROPOSTAS

| # | Problema | Solução | Complexidade |
|---|----------|---------|-------------|
| 1 | handlers.py sintaxe | ✅ JÁ CORRIGIDO (f-string foi reparada) | Baixa |
| 2 | write_file 80% erro | Adicionar lock de ficheiro + fallback para temp dir | Média |
| 3 | Wakeup loop infinito | ✅ JÁ CORRIGIDO (reconfigure UTF-8 + logger.info em vez de print) | Baixa |

---

## IMPLEMENTAÇÃO — Solução mais simples

### O que foi feito (correções já aplicadas anteriormente):

1. **`tools/fs_tools.py`** — Substituído `print(f"🔧 Tools usando...")` por `logger.info(f"[Tools] REPO_DIR: {REPO_DIR}")` e adicionado `sys.stdout.reconfigure(encoding="utf-8")` no topo.

2. **`main.py`** — Adicionado `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` antes de qualquer print/import.

3. **`bot/handlers.py`** — F-string mal formatada foi corrigida (compila sem erros).

### Agora — Implementar correção para write_file:

O problema de 80% de erro no write_file precisa de:
- Locking por ficheiro para evitar contenção
- Fallback para diretório temporário se o caminho original falhar

