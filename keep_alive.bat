@echo off
title CORREOTO - KEEP ALIVE SYSTEM
color 0A

echo ============================================
echo    CORREOTO KEEP ALIVE SYSTEM v3.0
echo    Funciona 24/7 - NUNCA PARA!
echo ============================================
echo.

:LOOP
echo [%date% %time%] Verificando sistema...

:: 1. Verifica se main.py esta a correr
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] [!] main.py NAO esta a correr! A iniciar...
    start /B python main.py
    echo [%date% %time%] [+] main.py iniciado!
) else (
    echo [%date% %time%] [+] main.py OK
)

:: 2. Verifica se auto_reset_v2.py esta a correr
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
REM Vamos verificar de outra forma - ver se o processo especifico existe
wmic process where "name='python.exe' and commandline like '%%auto_reset_v2%%'" get processid 2>NUL | findstr /R /C:"[0-9]" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] [!] auto_reset_v2 NAO esta a correr! A iniciar...
    start /B python auto_reset_v2.py
    echo [%date% %time%] [+] auto_reset_v2 iniciado!
) else (
    echo [%date% %time%] [+] auto_reset_v2 OK
)

:: 3. Verifica se o ficheiro de sinalizacao de paragem existe
if exist STOP_SIGNAL.flg (
    echo [%date% %time%] [!] Sinal de paragem detetado! A reiniciar tudo...
    del STOP_SIGNAL.flg
    taskkill /F /IM python.exe 2>NUL
    timeout /T 2 /NOBREAK >NUL
    start /B python main.py
    start /B python auto_reset_v2.py
    echo [%date% %time%} [+] Sistema reiniciado!
)

:: 4. Verifica se o ficheiro de heartbeat esta atualizado
if exist heartbeat.flg (
    for %%a in (heartbeat.flg) do set "ftime=%%~ta"
    REM Se o heartbeat tem mais de 60 segundos, algo esta errado
) else (
    echo [%date% %time%] [!] heartbeat.flg nao encontrado! A criar...
    echo %date% %time% > heartbeat.flg
)

:: 5. Verifica logs por "limite de iteracoes"
findstr /M "limite de itera" auto_reset_v2.log 2>NUL >NUL
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] [!] Limite de iteracoes detetado no log! A reiniciar...
    taskkill /F /IM python.exe 2>NUL
    timeout /T 3 /NOBREAK >NUL
    start /B python auto_reset_v2.py
    start /B python main.py
    echo [%date% %time%] [+] Reiniciado apos limite de iteracoes!
)

echo ----------------------------------------
timeout /T 5 /NOBREAK >NUL
goto LOOP
