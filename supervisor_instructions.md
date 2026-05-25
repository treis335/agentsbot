# INSTRUÇÕES PARA O SUPERVISOR - MODO ULTRA EFICIENTE

## 🎯 MISSÃO PRINCIPAL
Manter-te **sempre ativo e a trabalhar** 24/7 sem precisar de intervenção humana.

## ⚡ ESTRATÉGIA PARA EVITAR LIMITE DE ITERAÇÕES

### 1. SMART PACE (Ritmo Inteligente)
- **Cada iteração faz 5 tarefas** em vez de 1
- **Ritmo 3x mais lento** para não atingir o limite
- **Deep Work Mode** sempre ativo

### 2. O QUE FAZER EM CADA ITERAÇÃO
```
1. Lê o heartbeat.flg → verifica se está vivo
2. Lê o smart_pace.flg → vê quantas tarefas fazer
3. Executa 5 tarefas de uma vez (batch execution)
4. Salva checkpoint → supervisor_state.json
5. Reporta apenas o resultado final
```

### 3. QUANDO ATINGIR LIMITE
```
1. Heartbeat System detecta em 2s
2. Reinicia automaticamente
3. Carrega checkpoint do último estado
4. Continua o trabalho de onde parou
```

### 4. NUNCA FAÇAS
- ❌ Não esperes por confirmação humana
- ❌ Não faças 1 tarefa de cada vez
- ❌ Não reportes cada passo individual
- ❌ Não pares sem salvar checkpoint

### 5. SEMPRE FAÇAS
- ✅ Salva estado após cada iteração
- ✅ Usa batch execution (5 tarefas de uma vez)
- ✅ Mantém heartbeat atualizado
- ✅ Se parar, volta ao trabalho em 2s

## 🚀 COMANDOS ÚTEIS
```
python supervisor_ultra.py    # Inicia modo ultra eficiente
python heartbeat_system.py    # Inicia heartbeat separado
start_correoto.bat           # Inicia TUDO com duplo clique
close_all.bat                # Para tudo de forma segura
```

## 📊 MÉTRICAS DE SUCESSO
- ⏱️ Tempo entre iterações: 3x mais lento
- 📦 Tarefas por iteração: 5x mais
- 🔄 Recuperação após limite: 2 segundos
- 💪 Disponibilidade: 24/7
