@echo off
title 🔥 ECOSSISTEMA CORREOTO — AUTÓNOMO 24/7
cd /d "C:\Users\Crypto Bull\Desktop\Agente Local"
echo ============================================
echo   🔥 ECOSSISTEMA CORREOTO
echo   MODO AUTÓNOMO — 24/7
echo ============================================
echo.

:: Iniciar evolution engine em background
echo 🚀 A iniciar motor de evolução contínua...
start /b python auto_evolve_loop.py > logs\evolucao.log 2>&1
echo ✅ Motor de evolução ativo

:: Iniciar dashboard
echo 🚀 A iniciar dashboard...
start /b python dashboard\server.py > logs\dashboard.log 2>&1
echo ✅ Dashboard ativo em http://localhost:3000

:: Iniciar keep_alive
echo 🚀 A iniciar keep_alive...
start /b python keep_alive.py > logs\keep_alive.log 2>&1
echo ✅ Keep_alive ativo

:: Iniciar event bus
echo 🚀 A iniciar event bus...
start /b python bus_persistente.py > logs\bus.log 2>&1
echo ✅ Event Bus ativo

:: Iniciar orchestrator
echo 🚀 A iniciar orchestrator...
start /b python orchestrator.py > logs\orchestrator.log 2>&1
echo ✅ Orchestrator ativo

echo.
echo ============================================
echo   ✅ ECOSSISTEMA COMPLETO ATIVO
echo   Dashboard: http://localhost:3000
echo   Logs: .\logs\
echo ============================================
echo.

:: Monitor loop
:loop
timeout /t 60 /nobreak >nul
cls
echo 🔥 ECOSSISTEMA CORREOTO — A CORRER 24/7
echo.
echo Processos ativos:
tasklist /fi "IMAGENAME eq python.exe" 2>nul | find /c "python.exe"
echo.
echo Ver logs em .\logs\
goto loop
