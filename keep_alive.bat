@echo off
title CORREOTO KEEP ALIVE MONITOR
color 0C

echo ============================================
echo    KEEP ALIVE MONITOR v4.0
echo    A monitorizar processos...
echo ============================================
echo.

:loop
cls
echo [%date% %time%] - A verificar processos...

:: Verificar Heartbeat System
tasklist /FI "WINDOWTITLE eq Heartbeat System" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo [!] Heartbeat System MORTO! A reiniciar...
    start "Heartbeat System" python heartbeat_system.py
) else (
    echo [OK] Heartbeat System: ATIVO
)

:: Verificar se heartbeat.flg existe e é recente
if exist heartbeat.flg (
    for %%a in (heartbeat.flg) do set "filetime=%%~ta"
    echo [OK] Heartbeat file: %filetime%
) else (
    echo [!] Heartbeat file AUSENTE!
)

:: Verificar Smart Pace
if exist smart_pace.flg (
    echo [OK] Smart Pace: ATIVO
) else (
    echo [OK] Smart Pace: AGUARDANDO
)

:: Verificar Deep Work
if exist deep_work.flg (
    echo [OK] Deep Work Mode: ATIVO
) else (
    echo [OK] Deep Work Mode: AGUARDANDO
)

:: Mostrar status resumido
echo.
echo --- STATUS ATUAL ---
python -c "
import json, os
try:
    if os.path.exists('smart_pace.flg'):
        with open('smart_pace.flg') as f:
            d = json.load(f)
        print(f'Iteracoes: {d.get(\"iteration_count\", \"?\")}')
        print(f'Modo: {\"DEEP WORK\" if d.get(\"deep_work_mode\") else (\"SLOW\" if d.get(\"slow_mode\") else \"NORMAL\")}')
        print(f'Pace: {d.get(\"pace_factor\", 1.0)}x')
except: pass
"
echo.

echo A aguardar 10 segundos...
timeout /T 10 /NOBREAK >NUL
goto loop
