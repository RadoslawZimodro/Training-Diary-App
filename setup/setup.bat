@echo off
chcp 65001 >nul

REM Training Diary - Setup Script (Windows)
REM Automatyczna konfiguracja środowiska Docker

echo  Training Diary - Setup Script (Windows) 
echo ==========================================

REM Sprawdź czy Docker jest zainstalowany
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker nie jest zainstalowany. Zainstaluj Docker Desktop.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker Compose nie jest zainstalowany.
    pause
    exit /b 1
)

echo  Docker i Docker Compose są dostępne

REM Stwórz potrzebne katalogi
echo  Tworzenie katalogów...
if not exist "mongo-init" mkdir mongo-init
if not exist "data" mkdir data
if not exist "data\mongodb" mkdir data\mongodb
if not exist "data\redis" mkdir data\redis

REM Sprawdź czy pliki konfiguracyjne istnieją
if not exist "docker-compose.yml" (
    echo  Nie znaleziono docker-compose.yml
    pause
    exit /b 1
)

REM Uruchom kontenery
echo  Uruchamianie kontenerów...
docker-compose up -d

if %errorlevel% neq 0 (
    echo  Błąd uruchamiania kontenerów
    pause
    exit /b 1
)

REM Sprawdź status kontenerów
echo  Sprawdzanie statusu kontenerów...
timeout /t 10 /nobreak >nul

REM Sprawdź czy MongoDB jest gotowy
echo  Oczekiwanie na MongoDB...
set timeout_counter=30

:wait_mongodb
docker exec training_diary_mongo mongosh --eval "db.runCommand('ping')" >nul 2>&1
if %errorlevel% equ 0 goto mongodb_ready

timeout /t 2 /nobreak >nul
set /a timeout_counter-=1
if %timeout_counter% gtr 0 goto wait_mongodb

echo  Timeout - MongoDB nie odpowiada
pause
exit /b 1

:mongodb_ready
REM Inicjalizuj Replica Set
echo  Inicjalizacja MongoDB Replica Set...
docker exec training_diary_mongo mongosh --eval "try { rs.initiate({ _id: 'rs0', members: [{ _id: 0, host: 'localhost:27017' }] }); print('✅ Replica Set zainicjalizowany'); } catch(e) { if (e.message.includes('already initialized')) { print('✅ Replica Set już istnieje'); } else { print('❌ Błąd inicjalizacji Replica Set: ' + e.message); } }"

REM Sprawdź czy Redis jest gotowy
echo  Sprawdzanie Redis...
docker exec training_diary_redis redis-cli -a redis123 ping >nul 2>&1
if %errorlevel% equ 0 (
    echo  Redis działa poprawnie
) else (
    echo  Redis nie odpowiada
)

REM Wyświetl informacje o dostępnych serwisach
echo.
echo  Setup zakończony pomyślnie!
echo ================================
echo  Dostępne serwisy:
echo • MongoDB: localhost:27017
echo   - User: admin
echo   - Password: admin123
echo   - Database: training_diary
echo.
echo • Redis: localhost:6379
echo   - Password: redis123
echo.
echo • MongoDB Express (GUI): http://localhost:8081
echo   - User: admin
echo   - Password: admin123
echo.
echo • Redis Commander (GUI): http://localhost:8082
echo   - User: admin
echo   - Password: admin123
echo.
echo 🔧 Przydatne komendy:
echo • docker-compose logs -f           # Podgląd logów
echo • docker-compose down              # Zatrzymanie
echo • docker-compose restart           # Restart
echo • docker-compose down -v           # Zatrzymanie + usunięcie danych
echo.
echo  Teraz możesz uruchomić swoje skrypty Python!
echo    Pamiętaj o zainstalowaniu: pip install -r requirements.txt
echo.
pause