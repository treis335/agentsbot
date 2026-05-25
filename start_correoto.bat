@echo off
title CORREOTO - Ecossistema Automatico
color 0A

echo.
echo ╔══════════════════════════════════════════╗
echo ║     🚀 INICIAR ECOSSISTEMA CORREOTO     ║
echo ║     Todos os sistemas automaticos!       ║
echo ╚══════════════════════════════════════════╝
echo.

:: Verifica se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado! Instala Python primeiro.
    pause
    exit /b 1
)

echo ✅ Python encontrado
echo.

:: Inicia o orquestrador automatico
echo 🎯 A iniciar Orquestrador Automatico...
echo.
echo 📋 Sistemas que vao correr:
echo   1. WakeUp System (acorda a cada 1 minuto)
echo   2. Auto Recovery (recupera de falhas)
echo   3. Auto Evolve (aprende e evolui)
echo   4. Main (sistema principal)
echo.
echo ⏳ A carregar...
timeout /t 3 /nobreak >nul

:: Corre o orquestrador
python orchestrator_auto.py

:: Se falhar, tenta alternativas
if errorlevel 1 (
    echo.
    echo ⚠️ Orquestrador falhou. A tentar sistemas individuais...
    echo.
    
    :: Tenta cada sistema individualmente
    start "WakeUp" cmd /c python wakeup.py
    timeout /t 2 /nobreak >nul
    start "AutoEvolve" cmd /c python auto_evolve.py
    timeout /t 2 /nobreak >nul
    start "Main" cmd /c python main.py
    
    echo.
    echo ✅ Sistemas individuais iniciados!
)

echo.
echo ╔══════════════════════════════════════════╗
echo ║     ✅ ECOSSISTEMA EM EXECUCAO!         ║
echo ║     Fecha esta janela para parar        ║
echo ╚══════════════════════════════════════════╝
echo.

pause
