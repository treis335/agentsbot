@echo off
title CORREOTO - LAUNCHER DEFINITIVO
color 0B

echo ============================================
echo    CORREOTO ECOSYSTEM - LAUNCHER v3.0
echo    ******** NUNCA PARA! ********
echo ============================================
echo.
echo A iniciar todos os sistemas...
echo.

:: Mata processos python antigos
echo [1/5] A limpar processos antigos...
taskkill /F /IM python.exe 2>NUL
timeout /T 2 /NOBREAK >NUL

:: Inicia Heartbeat System (NUNCA para - corre em loop infinito)
echo [2/5] A iniciar Heartbeat System...
start "CORREOTO-Heartbeat" /MIN python heartbeat_system.py
timeout /T 1 /NOBREAK >NUL

:: Inicia Auto-Reset V2
echo [3/5] A iniciar Auto-Reset V2...
start "CORREOTO-AutoReset" /MIN python auto_reset_v2.py
timeout /T 1 /NOBREAK >NUL

:: Inicia Keep Alive Batch (monitoriza tudo)
echo [4/5] A iniciar Keep Alive Batch...
start "CORREOTO-KeepAlive" /MIN keep_alive.bat
timeout /T 1 /NOBREAK >NUL

:: Inicia Main
echo [5/5] A iniciar Main...
start "CORREOTO-Main" /MIN python main.py

echo.
echo ============================================
echo    TODOS OS SISTEMAS INICIADOS!
echo    Monitorizacao 24/7 ATIVA!
echo ============================================
echo.
echo Processos ativos:
tasklist /FI "IMAGENAME eq python.exe" 2>NUL
echo.
echo Para ver logs:
echo   - heartbeat_system.log
echo   - auto_reset_v2.log
echo   - keep_alive.log (no ecra do batch)
echo.
echo Para parar tudo: close_all.bat
echo.

:: Mantem esta janela aberta a mostrar o heartbeat
echo A monitorizar (atualiza a cada 5s)...
echo Pressiona CTRL+C para parar
echo.

:MONITOR_LOOP
cls
echo ============================================
echo    CORREOTO - MONITOR EM TEMPO REAL
echo    %date% %time%
echo ============================================
echo.

:: Mostra heartbeat
if exist heartbeat.flg (
    set /p hb=<heartbeat.flg
    echo Heartbeat: %hb%
) else (
    echo Heartbeat: SEM SINAL!
)

echo.
echo Processos Python:
tasklist /FI "IMAGENAME eq python.exe" 2>NUL
echo.

:: Verifica se heartbeat system esta vivo
wmic process where "name='python.exe' and commandline like '%%heartbeat%%'" get processid 2>NUL | findstr /R /C:"[0-9]" >NUL
if %ERRORLEVEL% EQU 0 (
    echo [OK] Heartbeat System: ATIVO
) else (
    echo [!!] Heartbeat System: MORTO! A reiniciar...
    start "CORREOTO-Heartbeat" /MIN python heartbeat_system.py
)

:: Verifica auto_reset
wmic process where "name='python.exe' and commandline like '%%auto_reset%%'" get processid 2>NUL | findstr /R /C:"[0-9]" >NUL
if %ERRORLEVEL% EQU 0 (
    echo [OK] Auto-Reset V2: ATIVO
) else (
    echo [!!] Auto-Reset V2: MORTO! A reiniciar...
    start "CORREOTO-AutoReset" /MIN python auto_reset_v2.py
)

:: Verifica main
wmic process where "name='python.exe' and commandline like '%%main.py%%'" get processid 2>NUL | findstr /R /C:"[0-9]" >NUL
if %ERRORLEVEL% EQU 0 (
    echo [OK] Main: ATIVO
) else (
    echo [!!] Main: MORTO! A reiniciar...
    start "CORREOTO-Main" /MIN python main.py
)

echo.
echo ----------------------------------------
echo Atualiza em 5 segundos...
timeout /T 5 /NOBREAK >NUL
goto MONITOR_LOOP
