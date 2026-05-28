# Correoto Agent - Auto Restart PowerShell Script
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Correoto Agent - Auto Restart Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$projectPath = "C:\Users\Crypto Bull\Desktop\Agente Local"
Set-Location $projectPath

# Step 1: Kill Docker containers
Write-Host "[1/5] A matar containers Docker..." -ForegroundColor Yellow
try {
    docker-compose down 2>$null
    docker kill correoto-agent 2>$null
    Write-Host " OK - Containers eliminados" -ForegroundColor Green
} catch {
    Write-Host " OK - Sem containers Docker ativos" -ForegroundColor Green
}

# Step 2: Configure .env
Write-Host "[2/5] A verificar configuracao..." -ForegroundColor Yellow
$envPath = Join-Path $projectPath ".env"
if (-not (Test-Path $envPath)) {
    @"
SANDBOX_ENABLED=false
DEEPSEEK_API_KEY=
GITHUB_TOKEN=
REPO_LOCAL_PATH=C:\Users\Crypto Bull\Desktop\Agente Local
"@ | Set-Content $envPath
    Write-Host " OK - Ficheiro .env criado" -ForegroundColor Green
} else {
    $content = Get-Content $envPath -Raw
    if ($content -match "SANDBOX_ENABLED=true") {
        $content = $content -replace "SANDBOX_ENABLED=true", "SANDBOX_ENABLED=false"
        Set-Content $envPath $content
        Write-Host " OK - SANDBOX_ENABLED alterado para false" -ForegroundColor Green
    } else {
        Write-Host " OK - SANDBOX_ENABLED ja esta false" -ForegroundColor Green
    }
}

# Step 3: Check Python
Write-Host "[3/5] A verificar Python..." -ForegroundColor Yellow
try {
    $pyVersion = python --version
    Write-Host " OK - Python encontrado: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host " ERRO: Python nao encontrado! Instala Python primeiro." -ForegroundColor Red
    Read-Host "Prima Enter para sair"
    exit 1
}

# Step 4: Install dependencies
Write-Host "[4/5] A verificar dependencias..." -ForegroundColor Yellow
$reqPath = Join-Path $projectPath "requirements.txt"
if (Test-Path $reqPath) {
    pip install -r $reqPath --quiet 2>$null
    Write-Host " OK - Dependencias instaladas" -ForegroundColor Green
} else {
    Write-Host " OK - Sem requirements.txt" -ForegroundColor Green
}

# Step 5: Start agent
Write-Host "[5/5] A iniciar agente..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Agente a correr em modo NATIVO (Windows)" -ForegroundColor Cyan
Write-Host " CTRL+C para parar" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

python main.py

Write-Host ""
Write-Host "Agente terminou." -ForegroundColor Red
Read-Host "Prima Enter para sair"
