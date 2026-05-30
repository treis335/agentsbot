import socket
import json

try:
    s = socket.socket()
    s.settimeout(10)
    s.connect(('127.0.0.1', 9999))
    
    comando = {
        'acao': 'git_push',
        'mensagem': 'Forçar sincronização completa - Supervisor'
    }
    
    s.send(json.dumps(comando).encode())
    resposta = s.recv(4096).decode()
    print(f'[OK] Resposta: {resposta}')
    s.close()
except Exception as e:
    print(f'[X] Erro: {e}')
