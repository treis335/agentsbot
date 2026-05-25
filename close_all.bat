@echo off
title CORREOTO - SHUTDOWN
color 0C

echo ============================================
echo    A PARAR TODOS OS SISTEMAS CORREOTO...
echo ============================================
echo.

:: Cria sinal de paragem
echo STOP > STOP_SIGNAL.flg

:: Mata todos os processos python
echo [1/3] A parar processos Python...
taskkill /F /IM python.exe 2>NUL
timeout /T 2 /NOBREAK >NUL

:: Mata os batchs
echo [2/3] A parar processos batch...
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq CORREOTO*" 2>NUL
timeout /T 1 /NOBREAK >NUL

:: Limpa ficheiros temporarios
echo [3/3] A limpar ficheiros temporarios...
if exist STOP_SIGNAL.flg del STOP_SIGNAL.flg
if exist heartbeat.flg del heartbeat.flg

echo.
echo ============================================
echo    SISTEMAS CORREOTO PARADOS COM SUCESSO!
echo ============================================
echo.
echo Para reiniciar: launch_correoto.bat
echo.
pause
