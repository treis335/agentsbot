# Aprendizagem do Repositório awesome-deepseek-agent

## Resumo
Explorei o repositório [awesome-deepseek-agent](https://github.com/deepseek-ai/awesome-deepseek-agent) que contém guias de integração do DeepSeek em ferramentas de agentes IA.

## Ferramentas Analisadas

### 1. LobeHub — Chief Agent Operator
- **Conceito**: Organiza agentes em operação 24/7, contrata, agenda, reporta
- **Para o Correoto**: Modelo de "operador chefe de agentes" — o Supervisor deve ser o LobeHub do ecossistema
- **Aprendizagem**: Interface visual para gestão de equipa de agentes

### 2. Hermes (Nous Research) — Self-Improving Agent
- **Conceito**: Loop de aprendizagem embutido — cria skills da experiência, melhora-as durante uso, persiste conhecimento
- **Para o Correoto**: Implementar learning loop — agentes aprendem com erros passados
- **Aprendizagem**: `skills/` diretório para skills que evoluem com uso

### 3. DeepSeek-TUI — Sandboxed Tool Execution
- **Conceito**: Codex-style em Rust, sandboxing (Seatbelt macOS, Landlock Linux, Windows), MCP client+server, sub-agentes, RLM
- **Para o Correoto**: Sandboxing para execução segura de código, sub-agentes via `agent_spawn`
- **Aprendizagem**: MCP (Model Context Protocol) como padrão de comunicação entre agentes

### 4. Deep Code — Agent Skills
- **Conceito**: Skills descobertas de `~/.agents/skills/<name>/SKILL.md` e projeto-local
- **Para o Correoto**: Skills como módulos independentes descobertos dinamicamente
- **Aprendizagem**: Raciocínio configurável (reasoning effort: max/high)

### 5. Oh My Pi — Configuração de Reasoning
- **Conceito**: Mapeamento detalhado de reasoning effort (minLevel/maxLevel)
- **Para o Correoto**: Configuração fina de reasoning para DeepSeek
- **Aprendizagem**: `supportsReasoningEffort`, `reasoningEffortMap`, `extraBody.thinking`

### 6. Crush — Multi-model + LSP + MCP
- **Conceito**: Suporte multi-modelo, integração LSP, servidores MCP
- **Para o Correoto**: Suporte a múltiplos providers (DeepSeek, OpenAI, Anthropic)

### 7. nanobot — Leve + Memória + MCP
- **Conceito**: Agente leve com integração chat, memória, MCP
- **Para o Correoto**: Arquitetura minimalista como referência

### 8. Claude Code — Integração DeepSeek via Anthropic API
- **Conceito**: Usa `ANTHROPIC_BASE_URL` apontando para `api.deepseek.com/anthropic`
- **Para o Correoto**: Provider-agnóstico — um agente pode usar qualquer API

### 9. Codex + Moon Bridge — Forwarding Layer
- **Conceito**: Moon Bridge como camada de tradução entre OpenAI Responses API e DeepSeek
- **Para o Correoto**: Bridge pattern para compatibilidade entre APIs

### 10. AstrBot — Multi-plataforma + MCP + Plugins
- **Conceito**: Suporte QQ, WeChat, Feishu, Telegram; extensível com skills, plugins, MCPs
- **Para o Correoto**: Arquitetura de plugins para extensibilidade

## Melhorias a Aplicar no Correoto

### 1. MCP (Model Context Protocol) Support
Implementar servidor MCP para que agentes comuniquem via protocolo padrão.

### 2. Sandboxing
Adicionar sandboxing para execução segura de código (como DeepSeek-TUI faz).

### 3. Cache Layer
Cache de reasoning (como Reasonix) para evitar recomputar respostas idênticas.

### 4. Auto-Repair Loop
Loop de auto-reparação baseado em erros (como Hermes).

### 5. Learning from Experience
Agentes que aprendem com erros passados e melhoram continuamente.

### 6. Skills Modulares
Skills como diretórios independentes com SKILL.md.

### 7. Multi-Provider Support
Suporte a DeepSeek, OpenAI, Anthropic como providers intercambiáveis.

### 8. Reasoning Effort Configurável
Controle fino de reasoning effort (high/max).

### 9. Sub-Agents
Capacidade de spawnar sub-agentes para tarefas complexas.

### 10. Runtime API
API HTTP para expor o ecossistema (como deepseek serve --http).
