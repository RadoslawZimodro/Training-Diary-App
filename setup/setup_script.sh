#!/bin/bash

# Training Diary - Setup Script
# Automatyczna konfiguracja środowiska Docker

echo "🏋️ Training Diary - Setup Script 🏋️"
echo "======================================"

# Sprawdź czy Docker jest zainstalowany
if ! command -v docker &> /dev/null; then
    echo "❌ Docker nie jest zainstalowany. Zainstaluj Docker Desktop."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose nie jest zainstalowany."
    exit 1
fi

echo "✅ Docker i Docker Compose są dostępne"

# Stwórz potrzebne katalogi
echo "📁 Tworzenie katalogów..."
mkdir -p mongo-init
mkdir -p data/mongodb
mkdir -p data/redis

# Sprawdź czy pliki konfiguracyjne istnieją
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Nie znaleziono docker-compose.yml"
    exit 1
fi

# Uruchom kontenery
echo "🚀 Uruchamianie kontenerów..."
docker-compose up -d

# Sprawdź status kontenerów
echo "⏳ Sprawdzanie statusu kontenerów..."
sleep 10

# Sprawdź czy MongoDB jest gotowy
echo "🔄 Oczekiwanie na MongoDB..."
timeout=60
while ! docker exec training_diary_mongo mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; do
    sleep 2
    timeout=$((timeout-2))
    if [ $timeout -le 0 ]; then
        echo "❌ Timeout - MongoDB nie odpowiada"
        exit 1
    fi
done

# Inicjalizuj Replica Set
echo "⚙️ Inicjalizacja MongoDB Replica Set..."
docker exec training_diary_mongo mongosh --eval "
try {
    rs.initiate({
        _id: 'rs0',
        members: [
            { _id: 0, host: 'localhost:27017' }
        ]
    });
    print('✅ Replica Set zainicjalizowany');
} catch(e) {
    if (e.message.includes('already initialized')) {
        print('✅ Replica Set już istnieje');
    } else {
        print('❌ Błąd inicjalizacji Replica Set: ' + e.message);
    }
}
"

# Sprawdź czy Redis jest gotowy
echo "🔄 Sprawdzanie Redis..."
if docker exec training_diary_redis redis-cli -a redis123 ping > /dev/null 2>&1; then
    echo "✅ Redis działa poprawnie"
else
    echo "❌ Redis nie odpowiada"
fi

# Wyświetl informacje o dostępnych serwisach
echo ""
echo "🎉 Setup zakończony pomyślnie!"
echo "================================"
echo "📊 Dostępne serwisy:"
echo "• MongoDB: localhost:27017"
echo "  - User: admin"
echo "  - Password: admin123"
echo "  - Database: training_diary"
echo ""
echo "• Redis: localhost:6379"
echo "  - Password: redis123"
echo ""
echo "• MongoDB Express (GUI): http://localhost:8081"
echo "  - User: admin"
echo "  - Password: admin123"
echo ""
echo "• Redis Commander (GUI): http://localhost:8082"
echo "  - User: admin"
echo "  - Password: admin123"
echo ""
echo "🔧 Przydatne komendy:"
echo "• docker-compose logs -f           # Podgląd logów"
echo "• docker-compose down              # Zatrzymanie"
echo "• docker-compose restart           # Restart"
echo "• docker-compose down -v           # Zatrzymanie + usunięcie danych"
echo ""
echo "🚀 Teraz możesz uruchomić swoje skrypty Python!"
echo "   Pamiętaj o zainstalowaniu: pip install pymongo redis"