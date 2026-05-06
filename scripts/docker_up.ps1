# RestorAI – bring up the OEL Docker stack (Windows / PowerShell)
# Usage:  .\scripts\docker_up.ps1
# Prereqs: Docker Desktop installed and RUNNING (Linux engine).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

# Ensure .env exists (compose requires OPENAI_API_KEY to be set)
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[!] Created .env from .env.example – set a real OPENAI_API_KEY inside .env for working /chat." -ForegroundColor Yellow
}

Write-Host "[*] Checking Docker daemon..."
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] Docker daemon not reachable (Linux enginepipe missing)." -ForegroundColor Red
    Write-Host "    1) Open Docker Desktop" -ForegroundColor Yellow
    Write-Host "    2) Wait until the whale icon shows 'Docker Desktop is running'" -ForegroundColor Yellow
    Write-Host "    3) Run this script again from the project root:  .\scripts\docker_up.ps1" -ForegroundColor Yellow
    exit 1
}

docker compose version
Write-Host "[*] Building and starting services (this may take several minutes the first time)..."
docker compose up --build -d

Write-Host "`n[*] Service status:"
docker compose ps

Write-Host "`n[*] Health check (agent on localhost:8000):"
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 30
    Write-Host $r.Content
} catch {
    Write-Host "[!] /health not ready yet – wait ~30s and run:  curl http://localhost:8000/health" -ForegroundColor Yellow
}

Write-Host "`n[*] Optional – ingest knowledge base into the compose ChromaDB:"
Write-Host "    docker compose exec agent python -m app.ingestion.ingest_data"

Write-Host "`nDone."
