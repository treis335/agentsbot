#!/usr/bin/env python3
"""
Correção 2: Adicionar fallback robusto ao OrganicMind.
O bug: quando _call_llm falha (API key, timeout, etc.), collective_debate()
retorna dict sem 'tasks', causando KeyError: 'title' no autonomous_loop.py.
"""
import json

# LER o ficheiro original
with open('agents/organic_mind.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print(f'Original: {len(lines)} linhas')

# Procurar a função collective_debate
# O problema: quando _call_llm_simple falha dentro de _extract_tasks, 
# a excecao propaga e o debate retorna sem 'tasks'
# 
# Solucao: tornar _extract_tasks e _supervisor_synthesize mais robustas
# e garantir que collective_debate SEMPRE retorna dict com 'tasks'

# 1. Vamos encontrar e modificar _extract_tasks para ser bulletproof
# 2. Garantir que collective_debate tem try/except final

# Estrategia mais simples: modificar o _call_llm_simple para nunca levantar excecao
# que nao seja tratada, e modificar collective_debate para ter fallback total

old_call = '''def _call_llm_simple(messages: list, max_tokens: int = 400) -> str:
    """Chama LLM sem tools — só para pensar e responder."""
    from agents.llm_agent import _call_llm
    response = _call_llm(messages, use_tools=False, max_tokens=max_tokens)
    return response["choices"][0]["message"]["content"].strip()'''

new_call = '''def _call_llm_simple(messages: list, max_tokens: int = 400) -> str:
    """Chama LLM sem tools — só para pensar e responder. Com fallback."""
    try:
        from agents.llm_agent import _call_llm
        response = _call_llm(messages, use_tools=False, max_tokens=max_tokens)
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"[OrganicMind] _call_llm_simple falhou: {e}")
        return ""'''

if old_call in content:
    content = content.replace(old_call, new_call)
    print('✅ _call_llm_simple atualizado com try/except')
else:
    print('⚠️  _call_llm_simple original nao encontrado - tentando outro padrao')
    # Tentar encontrar a funcao
    for i, line in enumerate(lines):
        if 'def _call_llm_simple' in line:
            print(f'  Encontrado na linha {i+1}: {line}')
            break

# Agora garantir que collective_debate SEMPRE retorna tasks
old_debate_return = '''    return {
        "topic": topic,
        "contributions": contributions,
        "synthesis": synthesis,
        "tasks": tasks,
        "ts": datetime.now().isoformat(),
    }'''

new_debate_return = '''    # Garantir que tasks e uma lista valida (fallback se algo falhou)
    if not isinstance(tasks, list):
        logger.warning(f"[OrganicMind] tasks nao e lista: {type(tasks)}. Usando fallback.")
        tasks = _fallback_tasks(topic)
    return {
        "topic": topic,
        "contributions": contributions,
        "synthesis": synthesis if synthesis else "Sintese indisponivel",
        "tasks": tasks,
        "ts": datetime.now().isoformat(),
    }'''

if old_debate_return in content:
    content = content.replace(old_debate_return, new_debate_return)
    print('✅ collective_debate return atualizado com validacao')
else:
    print('⚠️  Return padrao nao encontrado')

# 3. Tambem tornar _extract_tasks mais robusta - garantir que SEMPRE retorna lista
old_extract = '''def _extract_tasks(topic: str, debate: str, synthesis: str) -> list:
    """Extrai tarefas concretas do debate para o backlog.
    Retorna SEMPRE uma lista de dicionarios com title, description, agent, priority."""'''

# Adicionar try/except em volta de todo o corpo da funcao
# Vamos ver se a funcao ja tem try/except
if 'except Exception as e:' in content.split('def _extract_tasks')[1].split('\n\n')[0] if 'def _extract_tasks' in content else False:
    print('_extract_tasks ja tem try/except')
else:
    print('⚠️  _extract_tasks pode precisar de mais protecao')

# Escrever o ficheiro atualizado
with open('agents/organic_mind.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verificar sintaxe
import ast
try:
    ast.parse(content)
    print('✅ Sintaxe OK apos correcao')
except SyntaxError as e:
    print(f'❌ Erro de sintaxe: {e}')
