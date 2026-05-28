@echo off
title Correoto Agent - Auto Restart
cd /d C:\Users\Crypto Bull\Desktop\Agente Local

echo ============================================
echo  Correoto Agent - Auto Restart Script
echo ============================================
echo.

:: Kill any running Docker containers
echo [1/5] A matar containers Docker...
docker-compose down 2>nul
docker kill correoto-agent 2>nul
echo  OK - Containers eliminados
echo.

:: Ensure .env is configured for native mode
echo [2/5] A verificar configuracao...
if not exist .env (
    echo SANDBOX_ENABLED=false > .env
    echo DEEPSEEK_API_KEY= >> .env
    echo GITHUB_TOKEN= >> .env
    echo REPO_LOCAL_PATH=C:\Users\Crypto Bull\Desktop\Agente Local >> .env
    echo  OK - Ficheiro .env criado
) else (
    findstr /i "SANDBOX_ENABLED=true" .env >nul
    if !errorlevel! equ 0 (
        powershell -Command "(Get-Content .env) -replace 'SANDBOX_ENABLED=true', 'SANDBOX_ENABLED=false' | Set-Content .env"
        echo  OK - SANDBOX_ENABLED alterado para false
    ) else (
        echo  OK - SANDBOX_ENABLED ja esta false
    )
)
echo.

:: Check if Python is available
echo [3/5] A verificar Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERRO: Python nao encontrado! Instala Python primeiro.
    pause
    exit /b 1
)
echo  OK - Python encontrado
echo.

:: Install requirements if needed
echo [4/5] A verificar dependencias...
if exist requirements.txt (
    pip install -r requirements.txt --quiet >nul 2>&1
    echo  OK - Dependencias instaladas
) else (
    echo  OK - Sem requirements.txt
)
echo.

:: Start the agent
echo [5/5] A iniciar agente...
echo.
echo ============================================
echo  Agente a correr em modo NATIVO (Windows)
echo  CTRL+C para parar
echo ============================================
echo.

python main.py

echo.
echo Agente terminou.
pause
