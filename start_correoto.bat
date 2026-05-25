@echo off
title CORREOTO ECOSYSTEM - AUTO RESET
color 0A

echo ========================================
echo    CORREOTO ECOSYSTEM - AUTO RESET
echo    WakeUp em 3 segundos!
echo ========================================
echo.

:: Inicia o Auto-Reset System (monitoriza e reinicia)
echo [1/3] A iniciar Auto-Reset System...
start "Auto-Reset" /min python auto_reset.py

timeout /t 2 /nobreak >nul

:: Inicia o WakeUp V3 (ultra rapido)
echo [2/3] A iniciar WakeUp V3...
start "WakeUp-V3" /min python wakeup_v3.py

timeout /t 2 /nobreak >nul

:: Inicia o sistema principal
echo [3/3] A iniciar sistema principal...
start "Correoto-Main" python main.py

echo.
echo ========================================
echo    SISTEMA CORREOTO ATIVO!
echo    Auto-reset em 3 segundos
echo    Nao precisa de intervencao!
echo ========================================
echo.
echo Pressiona CTRL+C para parar tudo
echo.

:loop
timeout /t 10 /nobreak >nul
goto loop
