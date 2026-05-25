@echo off
title CORREOTO ECOSYSTEM v5.0 - ULTRA EFICIENTE
color 0A

echo ============================================
echo    CORREOTO ECOSYSTEM v5.0
echo    MODO ULTRA EFICIENTE
echo    Solucao definitiva para limite de iteracoes!
echo ============================================
echo.

:: Limpar ficheiros temporarios
echo [1/6] A limpar estado anterior...
if exist supervisor_state.json del supervisor_state.json
if exist smart_pace.flg del smart_pace.flg
if exist deep_work.flg del deep_work.flg
if exist heartbeat.flg del heartbeat.flg
echo.

:: Ativar Smart Pace System (slow mode preventivo)
echo [2/6] A ativar Smart Pace System...
python -c "
import json
data = {
    'iteration_count': 0,
    'deep_work_mode': True,
    'slow_mode': True,
    'pace_factor': 3.0,
    'tasks_per_iteration': 5,
    'last_reset': '2026-05-26T00:00:00'
}
with open('smart_pace.flg', 'w') as f:
    json.dump(data, f, indent=2)
print('Smart Pace ativo!')
"
echo.

:: Ativar Deep Work Mode
echo [3/6] A ativar Deep Work Mode...
python -c "
import json
data = {
    'active': True,
    'strategies': {
        'batch_execution': True,
        'full_analysis': True,
        'predictive_caching': True,
        'result_bundling': True,
        'parallel_thinking': True,
        'skip_confirmations': True
    },
    'economy_factor': 5.0
}
with open('deep_work.flg', 'w') as f:
    json.dump(data, f, indent=2)
print('Deep Work ativo!')
"
echo.

:: Iniciar Heartbeat System (em nova janela)
echo [4/6] A iniciar Heartbeat System...
start "Heartbeat System" python heartbeat_system.py
echo.

:: Iniciar Keep Alive (em nova janela)
echo [5/6] A iniciar Keep Alive Monitor...
start "Keep Alive" keep_alive.bat
echo.

:: Iniciar Supervisor Ultra-Eficiente
echo [6/6] A iniciar Supervisor Ultra-Eficiente...
echo.
echo ============================================
echo    TODOS OS SISTEMAS ATIVOS!
echo    Smart Pace: OK (3x mais lento, 5x mais trabalho)
echo    Deep Work: OK (5x mais eficiente)
echo    Heartbeat: OK (monitoriza 24/7)
echo    Keep Alive: OK (recupera em segundos)
echo.
echo    MODO ULTRA EFICIENTE:
echo    - Cada iteracao faz 5 tarefas
echo    - Ritmo 3x mais lento (evita limite)
echo    - Auto-recuperacao em 2 segundos
echo    - Checkpoint salva progresso
echo.
echo    A abrir Supervisor Principal...
echo ============================================
echo.

:: Executa supervisor ultra (que gere main.py)
python supervisor_ultra.py

echo.
echo Supervisor terminou. Heartbeat e Keep Alive continuam ativos.
echo Para parar tudo, execute close_all.bat
pause
