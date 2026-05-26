# Setup Ollama — Local Inference Layer (Batch 6)

Ollama corre modelos LLM localmente. Depois de configurado, o agentsbot
usa-o automaticamente para tarefas simples/repetitivas, poupando 60-80%
nas chamadas ao DeepSeek.

---

## 1. Instalar Ollama

### Linux / WSL
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS
```bash
brew install ollama
```

### Windows
Descarregar o installer em https://ollama.com/download/windows

---

## 2. Arrancar o servidor

```bash
ollama serve
# Fica a correr em http://localhost:11434
```

Para arrancar em background (systemd):
```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

---

## 3. Instalar modelos recomendados

### Modelo principal — código (recomendado)
```bash
ollama pull qwen2.5-coder:7b
# ~4.7 GB | Excelente para Python, fix de bugs, docstrings
```

### Modelo leve — classificação e texto simples
```bash
ollama pull llama3.2:3b
# ~2.0 GB | Muito rápido, bom para routing e sumários
```

### Modelo alternativo — raciocínio geral
```bash
ollama pull mistral:7b
# ~4.1 GB | Bom para análise e tarefas mistas
```

### Modelo avançado (se tiveres >16 GB RAM)
```bash
ollama pull qwen2.5-coder:14b
# ~8.7 GB | Melhor qualidade de código, mais lento
```

---

## 4. Configurar no agentsbot

Adicionar ao `.env`:

```env
# URL do servidor Ollama (default: localhost)
OLLAMA_URL=http://localhost:11434

# Modelo local preferido
LOCAL_MODEL=qwen2.5-coder:7b

# Threshold de routing: score abaixo disto → Ollama
# 0.0 = sempre DeepSeek | 1.0 = sempre Ollama | 0.4 = recomendado
ROUTING_THRESHOLD=0.4

# Timeout para Ollama em segundos (modelos grandes podem demorar)
OLLAMA_TIMEOUT=120
```

---

## 5. Verificar que está a funcionar

```bash
# Teste directo ao Ollama
ollama run qwen2.5-coder:7b "Escreve uma função Python que soma dois números"

# Listar modelos instalados
ollama list

# Ver o router do agentsbot
python -c "
import asyncio
from inference import router, registry

async def check():
    await registry.sync_local_models()
    client, model, decision = await router.get_client('list files in directory')
    print(f'Tarefa simples → {decision.provider}: {model}')
    
    client, model, decision = await router.get_client(
        'Refactorizar o sistema de autenticação para suportar OAuth2 com múltiplos providers'
    )
    print(f'Tarefa complexa → {decision.provider}: {model}')

asyncio.run(check())
"
```

Output esperado:
```
Tarefa simples   → ollama: qwen2.5-coder:7b
Tarefa complexa  → deepseek: deepseek-chat
```

---

## 6. Requisitos de hardware

| Modelo            | RAM Mínima | VRAM (GPU) | Velocidade tipica |
|-------------------|------------|------------|-------------------|
| llama3.2:3b       | 4 GB       | 4 GB       | ~30 tok/s (CPU)   |
| qwen2.5-coder:7b  | 8 GB       | 6 GB       | ~15 tok/s (CPU)   |
| mistral:7b        | 8 GB       | 6 GB       | ~15 tok/s (CPU)   |
| qwen2.5-coder:14b | 16 GB      | 12 GB      | ~8 tok/s (CPU)    |

**Sem GPU:** Ollama corre em CPU. É mais lento mas funciona.
Expectativa: qwen2.5-coder:7b demora ~10-30s por resposta em CPU.

**Com GPU (CUDA/Metal):** Ollama deteta automaticamente. 5-10x mais rápido.

---

## 7. Troubleshooting

### "Ollama não disponível"
```bash
# Verificar se está a correr
curl http://localhost:11434/api/tags

# Se não responder, arrancar manualmente
ollama serve
```

### "Modelo não encontrado"
```bash
# Listar modelos instalados
ollama list

# Fazer pull do modelo
ollama pull qwen2.5-coder:7b
```

### Routing a usar sempre DeepSeek
Ajustar `ROUTING_THRESHOLD` para um valor mais alto (ex: `0.6`) no `.env`.
Isso faz com que mais tarefas sejam classificadas como "simples" e enviadas ao Ollama.

### Ollama muito lento (>60s por resposta)
- Reduzir para um modelo mais pequeno: `LOCAL_MODEL=llama3.2:3b`
- Aumentar o timeout: `OLLAMA_TIMEOUT=180`
- Considerar modelo quantizado: `ollama pull qwen2.5-coder:7b-q4_0`

---

## 8. Economia estimada

Com `ROUTING_THRESHOLD=0.4` e Ollama a funcionar:

| Tipo de tarefa          | Frequência | Rota      |
|-------------------------|------------|-----------|
| git status, list files  | 30%        | Ollama ✓  |
| fix typo, add docstring | 25%        | Ollama ✓  |
| syntax check, lint      | 15%        | Ollama ✓  |
| refactor, nova feature  | 20%        | DeepSeek  |
| arquitectura, debug     | 10%        | DeepSeek  |

**Poupança estimada: 60-70% das chamadas DeepSeek.**
