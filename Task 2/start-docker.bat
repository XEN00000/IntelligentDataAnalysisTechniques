@echo off
REM  Smart Recipe - Docker Startup Script (Windows)
REM  To uruchomić: double-click tego pliku lub: start-docker.bat

setlocal enabledelayedexpansion

REM Sprawdź czy Docker jest zainstalowany
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Docker nie znaleziony!
    echo.
    echo Pobierz Docker Desktop: https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

REM Sprawdź czy Docker Desktop jest uruchomiony
docker ps >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⏳ Docker Desktop nie uruchomiony - uruchamiam...
    echo.
    
    REM Spróbuj uruchomić Docker Desktop
    if exist "C:\Program Files\Docker\Docker\Docker.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker.exe"
    ) else if exist "C:\Program Files (x86)\Docker\Docker\Docker.exe" (
        start "" "C:\Program Files (x86)\Docker\Docker\Docker.exe"
    ) else (
        echo ❌ Docker Desktop zainstalowany, ale nie znaleziony w domyślnej lokalizacji.
        echo Uruchom Docker Desktop ręcznie.
        pause
        exit /b 1
    )
    
    echo ⏳ Czekam na start Docker Desktop (30 sekund)...
    timeout /t 30 /nobreak
)

REM Teraz sprawdź czy faktycznie działa
docker ps >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Docker Desktop nie uzyskał dostępu. Spróbuj ponownie za 10 sekund.
    timeout /t 10 /nobreak
    exit /b 1
)

cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║      Smart Recipe - Docker Compose Startup                ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Sprawdź czy kontener już istnieje
docker ps -a | findstr "smart-recipe-ollama" >nul 2>&1
if !errorlevel! == 0 (
    echo ✓ Kontener smart-recipe-ollama znaleziony
    echo.
    echo ⏳ Uruchamiam kontener...
    docker-compose up -d
) else (
    echo ✓ Tworzę i uruchamiam nowy kontener...
    docker-compose up -d
)

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║               Trwa startup Ollama...                       ║
echo ║            (może trwać do 1 minuty za pierwszym razem)     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Czekaj na health check
setlocal enabledelayedexpansion
set "attempt=0"
set "max_attempts=30"

:waitloop
set /a attempt+=1
if !attempt! gtr !max_attempts! (
    echo.
    echo ⚠️  Timeout - sprawdź logami: docker-compose logs ollama
    goto :end
)

docker-compose ps | findstr "healthy" >nul 2>&1
if !errorlevel! == 0 (
    echo.
    echo ✅ Ollama gotowa!
    goto :success
)

docker-compose ps | findstr "smart-recipe-ollama" >nul 2>&1
if !errorlevel! == 0 (
    echo -n "."
    timeout /t 2 /nobreak >nul
    goto :waitloop
) else (
    echo ❌ Kontener się upadł - sprawdź: docker-compose logs ollama
    goto :end
)

:success
echo.
echo ✅ Docker Setup Zakończony!
echo.
echo Informacje:
echo   • Ollama server: http://localhost:11434
echo   • Aplikacja: uruchom normalnie
echo.
echo Następne kroki:
echo   1. Otwórz nowy terminal PowerShell
echo   2. Przejdź do folderu: cd "c:\Users\lukas_1b707ym\Documents\Studia\Semestr_6\IntelligentDataAnalysisTechniques\Task 2"
echo   3. Aktywuj venv: .\.venv\Scripts\Activate.ps1
echo   4. Uruchom: python main.py
echo.
echo Zarządzanie:
echo   Zatrzymaj: docker-compose stop
echo   Restart:   docker-compose restart
echo   Logami:    docker-compose logs -f ollama
echo.

:end
pause
