# Smart Recipe - Docker Startup Script (PowerShell)
# Uruchomienie: .\start-docker.ps1

function Write-Header {
    param([string]$Text)
    Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  $($Text.PadRight(56)) ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
}

function Test-Docker {
    try {
        docker --version | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-DockerRunning {
    try {
        docker ps | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Start-DockerDesktop {
    Write-Host "`n⏳ Docker Desktop nie uruchomiony - uruchamiam...`n" -ForegroundColor Yellow
    
    $dockerPath = "C:\Program Files\Docker\Docker\Docker.exe"
    if (Test-Path $dockerPath) {
        Start-Process $dockerPath
        Write-Host "⏳ Czekam na start Docker Desktop (30 sekund)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
    } else {
        Write-Host "❌ Docker Desktop zainstalowany, ale nie znaleziony." -ForegroundColor Red
        Write-Host "Uruchom Docker Desktop ręcznie i spróbuj ponownie." -ForegroundColor Red
        exit 1
    }
}

function Wait-OllamaHealthy {
    param([int]$MaxAttempts = 60)
    
    Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  Trwa startup Ollama...                                    ║" -ForegroundColor Cyan
    Write-Host "║  (może trwać do 1 minuty za pierwszym razem)               ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
    
    for ($i = 0; $i -lt $MaxAttempts; $i++) {
        $status = docker-compose ps | Select-String "healthy"
        if ($status) {
            return $true
        }
        
        # Sprawdź czy kontener istnieje
        $exists = docker-compose ps | Select-String "smart-recipe-ollama"
        if (-not $exists) {
            return $false
        }
        
        Write-Host -NoNewline "." -ForegroundColor Green
        Start-Sleep -Seconds 2
    }
    
    return $false
}

# === Main Script ===

Clear-Host
Write-Header "Smart Recipe - Docker Setup"

# 1. Sprawdź Docker
Write-Host "`n🔍 Sprawdzam Docker..." -ForegroundColor Cyan
if (-not (Test-Docker)) {
    Write-Host "`n❌ Docker nie znaleziony!" -ForegroundColor Red
    Write-Host "Pobierz Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    Read-Host "Naciśnij Enter aby wyjść"
    exit 1
}
Write-Host "✓ Docker zainstalowany" -ForegroundColor Green

# 2. Sprawdź czy Docker działa
Write-Host "🔍 Sprawdzam czy Docker Desktop działa..." -ForegroundColor Cyan
if (-not (Test-DockerRunning)) {
    Start-DockerDesktop
}
Write-Host "✓ Docker Desktop uruchomiony" -ForegroundColor Green

# 3. Sprawdź docker-compose
Write-Host "🔍 Sprawdzam docker-compose..." -ForegroundColor Cyan
try {
    docker-compose --version | Out-Null
    Write-Host "✓ docker-compose dostępny" -ForegroundColor Green
}
catch {
    Write-Host "`n❌ docker-compose nie znaleziony!" -ForegroundColor Red
    exit 1
}

# 4. Start kontainera
Write-Host "`n🚀 Uruchamiam Docker Compose...`n" -ForegroundColor Cyan
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Błąd podczas uruchomienia docker-compose!" -ForegroundColor Red
    Read-Host "Naciśnij Enter aby wyjść"
    exit 1
}

# 5. Czekaj na health check
Write-Host "`n" -ForegroundColor Green
if (Wait-OllamaHealthy) {
    Write-Host "`n`n✅ SUCCESS! Ollama Ready!`n" -ForegroundColor Green
    
    Write-Header "Docker Setup Zakończony"
    
    Write-Host "`nInformacje:
  • Ollama server: http://localhost:11434
  • Aplikacja: uruchom normalnie
" -ForegroundColor Cyan
    
    Write-Host "`nNastępne kroki:" -ForegroundColor Yellow
    Write-Host "  1. Otwórz nowy terminal PowerShell" -ForegroundColor White
    Write-Host "  2. Przejdź do folderu:" -ForegroundColor White
    Write-Host "     cd 'c:\Users\lukas_1b707ym\Documents\Studia\Semestr_6\IntelligentDataAnalysisTechniques\Task 2'" -ForegroundColor Gray
    Write-Host "  3. Aktywuj venv:" -ForegroundColor White
    Write-Host "     .\\.venv\\Scripts\\Activate.ps1" -ForegroundColor Gray
    Write-Host "  4. Uruchom:" -ForegroundColor White
    Write-Host "     python main.py" -ForegroundColor Gray
    
    Write-Host "`nZarządzanie:" -ForegroundColor Yellow
    Write-Host "  Zatrzymaj: docker-compose stop" -ForegroundColor Gray
    Write-Host "  Restart:   docker-compose restart" -ForegroundColor Gray
    Write-Host "  Logami:    docker-compose logs -f ollama" -ForegroundColor Gray
    
} else {
    Write-Host "`n⚠️  Timeout - Ollama nie uzyskał statusu healthy w czasie" -ForegroundColor Yellow
    Write-Host "Sprawdź logami:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs ollama" -ForegroundColor Gray
}

Write-Host "`n"
Read-Host "Naciśnij Enter aby wyjść"
