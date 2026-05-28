"""
core/grounding.py - Verificador de Realidade
Garante que o Supervisor so reporta acoes que realmente aconteceram.
"""

import json
import os
import subprocess

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Grounding:
    """Verificador de realidade - confirma acoes antes de reportar."""
    
    @staticmethod
    def file_exists(path):
        """Verifica se um ficheiro existe realmente."""
        full_path = os.path.join(PROJECT_DIR, path) if not os.path.isabs(path) else path
        return os.path.exists(full_path)
    
    @staticmethod
    def file_contains(path, text):
        """Verifica se um ficheiro contem determinado texto."""
        full_path = os.path.join(PROJECT_DIR, path) if not os.path.isabs(path) else path
        if not os.path.exists(full_path):
            return False
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return text in content
        except:
            return False
    
    @staticmethod
    def agent_exists(name):
        """Verifica se um agente existe no agents.json."""
        agents_path = os.path.join(PROJECT_DIR, 'agents.json')
        if not os.path.exists(agents_path):
            return False
        try:
            with open(agents_path, 'r', encoding='utf-8') as f:
                agents = json.load(f)
            return any(a.get('name') == name for a in agents)
        except:
            return False
    
    @staticmethod
    def git_log_contains(message):
        """Verifica se o git log contem uma mensagem especifica."""
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-10'],
                capture_output=True, text=True, cwd=PROJECT_DIR
            )
            return message.lower() in result.stdout.lower()
        except:
            return False
    
    @staticmethod
    def task_exists(task_id):
        """Verifica se uma tarefa existe no backlog."""
        backlog_path = os.path.join(PROJECT_DIR, 'memory', 'backlog.json')
        if not os.path.exists(backlog_path):
            return False
        try:
            with open(backlog_path, 'r', encoding='utf-8') as f:
                backlog = json.load(f)
            return any(t.get('id') == task_id for t in backlog)
        except:
            return False
    
    @staticmethod
    def verify_action(action_type, **kwargs):
        """
        Verifica se uma acao realmente ocorreu.
        
        action_type: 'file_created', 'file_modified', 'agent_created', 
                     'git_commit', 'task_added', 'system_rebooted'
        """
        if action_type == 'file_created':
            return Grounding.file_exists(kwargs.get('path', ''))
        
        elif action_type == 'file_modified':
            path = kwargs.get('path', '')
            content = kwargs.get('content', '')
            if content:
                return Grounding.file_contains(path, content)
            return Grounding.file_exists(path)
        
        elif action_type == 'agent_created':
            return Grounding.agent_exists(kwargs.get('name', ''))
        
        elif action_type == 'git_commit':
            return Grounding.git_log_contains(kwargs.get('message', ''))
        
        elif action_type == 'task_added':
            return Grounding.task_exists(kwargs.get('task_id', ''))
        
        elif action_type == 'system_rebooted':
            # Verificar pelo ficheiro de estado
            state_path = os.path.join(PROJECT_DIR, 'memory', 'state.json')
            if os.path.exists(state_path):
                try:
                    with open(state_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    last_boot = state.get('last_boot')
                    return last_boot is not None
                except:
                    pass
            return False
        
        return False
