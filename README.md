# Training-Diary-App

A backend application for tracking physical activity using Python, MongoDB and Redis. Created as a portfolio project to demonstrate backend and data management skills.

---

## 🛠️ Wymagania systemowe

### Oprogramowanie do zainstalowania:
- Python 3.8+ z pip
- Docker Desktop

---

## 🔧 Krok 1: Instalacja Python (Windows)

1. Wejdź na [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Pobierz najnowszą wersję Python (np. Python 3.12)
3. **WAŻNE:** Podczas instalacji zaznacz "Add Python to PATH"
4. Zainstaluj z domyślnymi ustawieniami

---

## 🐳 Krok 2: Instalacja Docker Desktop (Windows)

1. Wejdź na [https://docs.docker.com/desktop/install/windows/](https://docs.docker.com/desktop/install/windows/)
2. Pobierz Docker Desktop for Windows
3. Zainstaluj i uruchom Docker Desktop

---

## 📁 Krok 3: Przygotowanie plików projektu

1. Pobierz pliki repozytorium
2. Skopiuj wszystkie pliki projektu do jednego folderu

**Struktura plików:**
```
Training-Diary-App/
├── docker-compose.yml
├── training_diary.py
├── import_of_documents.py
├── deletion_of_data.py
├── document_generation_script.py
├── setup.bat
├── requirements.txt
├── users_10.json
├── trainings_10_users.json
├── friends.json
└── mongo-init/
    └── init.js
```

---

## ⚙️ Krok 4: Uruchomienie środowiska Docker

### Automatycznie (Windows):
```bash
setup.bat
```

**Oczekiwany wynik:**
```
Docker i Docker Compose są dostępne
Tworzenie katalogów...
Uruchamianie kontenerów...
Redis działa poprawnie
Setup zakończony pomyślnie!
```

### Ręcznie (jeśli setup.bat nie działa):
```bash
docker-compose up -d
```

---

## 🔍 Krok 5: Sprawdzenie statusu kontenerów

```bash
docker-compose ps
```

**Oczekiwany wynik:**
```
NAME                   STATUS
training_diary_mongo   Up
training_diary_redis   Up
```

---

## 🧩 Krok 6: Inicjalizacja MongoDB

```bash
docker exec training_diary_mongo mongosh --eval "rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'localhost:27017'}]})"
docker exec training_diary_mongo mongosh --eval "db.runCommand('ping')"
```

**Oczekiwany wynik:**
```
{ ok: 1 }
```

---

## 📦 Krok 7: Instalacja bibliotek Python

```bash
pip install pymongo redis python-dateutil
```

---

## 📥 Krok 8: Import danych testowych

### (Opcjonalnie) Wyczyść bazę:
```bash
python deletion_of_data.py
```

### Import danych:
```bash
python import_of_documents.py
```

**Oczekiwany wynik:**
```
Załadowano użytkowników.
Załadowano treningi.
Załadowano znajomych do kolekcji friends.
```

---

## 🚀 Krok 9: Uruchomienie aplikacji

```bash
python training_diary.py
```

**Oczekiwany wynik:**
```
Redis połączony!
Change stream listening for new trainings...
=== Training Diary App ===

1. Zaloguj się
2. Zarejestruj się
0. Zakończ
```

---

## 🧪 Krok 10: Test aplikacji

Zaloguj się danymi testowymi:

- Email: `bartek0@example.com`
- Hasło: `hashed_password_0`

**Przetestuj funkcje:**
- Opcja 2 – Wyświetl treningi
- Opcja 8 – Sprawdź serię treningową
- Opcja 9 – Zobacz ranking kalorii
- Opcja 10 – Sprawdź przypomnienie

---

## 🌐 Dostępne serwisy po instalacji

- MongoDB: `localhost:27017`
- Redis: `localhost:6379` (hasło: `redis123`)

---

## 🔁 Ponowne uruchomienie po restarcie

1. Uruchom Docker Desktop
2. Przejdź do katalogu projektu
3. Uruchom kontenery:
```bash
docker-compose up -d
```
4. Uruchom aplikację:
```bash
python training_diary.py
```
