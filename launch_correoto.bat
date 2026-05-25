@echo off
title CORREOTO ECOSYSTEM v4.0 - SMART PACING
color 0A

echo ============================================
echo    CORREOTO ECOSYSTEM v4.0 - SMART PACING
echo    Iniciando todos os sistemas...
echo ============================================
echo.

:: Ativar Smart Pace System (slow mode preventivo)
echo [1/5] A ativar Smart Pace System...
python -c "import smart_pace; smart_pace.reset_counter(); print('Smart Pace ativo!')"
echo.

:: Ativar Deep Work Mode
echo [2/5] A ativar Deep Work Mode...
python -c "import deep_work_mode; deep_work_mode.activate_deep_work(); print('Deep Work ativo!')"
echo.

:: Iniciar Heartbeat System (em nova janela)
echo [3/5] A iniciar Heartbeat System...
start "Heartbeat System" python heartbeat_system.py
echo.

:: Iniciar Keep Alive (em nova janela)
echo [4/5] A iniciar Keep Alive Monitor...
start "Keep Alive" keep_alive.bat
echo.

:: Iniciar Supervisor Principal
echo [5/5] A iniciar Supervisor Principal...
echo.
echo ============================================
echo    TODOS OS SISTEMAS ATIVOS!
echo    Heartbeat: OK
echo    Keep Alive: OK
echo    Smart Pace: OK
echo    Deep Work: OK
echo.
echo    A abrir Supervisor Principal...
echo ============================================
echo.

python main.py

echo.
echo Supervisor terminou. Heartbeat e Keep Alive continuam ativos.
echo Para parar tudo, execute close_all.bat
pause
