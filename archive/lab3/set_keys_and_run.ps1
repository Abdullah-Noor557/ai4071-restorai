# RestorAI Lab 3 - Setup and Run Script
# This script sets API keys and runs the demo

Write-Host "RestorAI Lab 3 - Setup Script" -ForegroundColor Cyan
Write-Host "="*70

# Prompt for OpenAI API key if not set
if (-not $env:OPENAI_API_KEY) {
    Write-Host "`n[!] OpenAI API key not found in environment" -ForegroundColor Yellow
    Write-Host "Please enter your OpenAI API key:" -ForegroundColor White
    Write-Host "(Get it from: https://platform.openai.com/api-keys)" -ForegroundColor Gray
    $apiKey = Read-Host -Prompt "API Key"
    $env:OPENAI_API_KEY = $apiKey
} else {
    Write-Host "`n[OK] Using existing OPENAI_API_KEY" -ForegroundColor Green
}

# Optional: Gemini API key
if (-not $env:GOOGLE_API_KEY) {
    Write-Host "`n[!] Google Gemini API key not set (optional for demo)" -ForegroundColor Yellow
    Write-Host "Press Enter to skip, or paste your Gemini API key:"
    $geminiKey = Read-Host -Prompt "Gemini Key (optional)"
    if ($geminiKey) {
        $env:GOOGLE_API_KEY = $geminiKey
    }
}

# Run the demo
Write-Host "`n" + "="*70
Write-Host "Running RestorAI Demo..." -ForegroundColor Cyan
Write-Host "="*70 + "`n"

python run_demo.py

Write-Host "`n" + "="*70
Write-Host "Demo Complete!" -ForegroundColor Green
Write-Host "="*70
