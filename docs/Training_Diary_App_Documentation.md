# Dzienniczek Treningowy - Analiza Implementacji

## MongoDB - Baza Dokumentowa

### **Struktura Kolekcji**

#### **1. Kolekcja `users`**
```javascript
{
  "_id": "ea7e65e1-ed41-498e-bfa7-13044ce76a9c",
  "username": "bartek880",
  "email": "bartek0@example.com", 
  "password_hash": "hashed_password_0",
  "age": 33,
  "gender": "female",
  "stats": {
    "total_trainings": 15,
    "total_calories": 2400,
    "total_minutes": 450
  }
}
```

#### **2. Kolekcja `trainings`**
```javascript
{
  "_id": ObjectId("..."),
  "user_id": "ea7e65e1-ed41-498e-bfa7-13044ce76a9c",
  "date": "2025-06-04",
  "type": "bieganie",
  "notes": "Trening typu bieganie...",
  "metrics": {
    "duration_min": 30,
    "calories_burned": 400,
    "distance_km": 5.0
  }
}
```

#### **3. Kolekcja `friends`**
```javascript
{
  "_id": ObjectId("..."),
  "user_id": "ea7e65e1-ed41-498e-bfa7-13044ce76a9c",
  "friends": [
    "edf89f89-dd20-44d5-831d-0a99e513d928",
    "95bd8bdc-b270-498a-b695-a53c187f9c73"
  ]
}
```

### **Specyficzne Właściwości MongoDB**

#### **1. Transakcje Wielodokumentowe**

**DEFINICJA:** Transakcje wielodokumentowe pozwalają wykonać kilka operacji na różnych dokumentach/kolekcjach jako jedną niepodzielną jednostkę. Albo wszystkie operacje się wykonają pomyślnie, albo żadna (zasada ACID - Atomicity).

**Implementacja w `add_training()`:**
```python
def add_training(user_id, training):
    with client.start_session() as session:
        with session.start_transaction():
            # Operacja 1: Zapisz trening
            trainings_col.insert_one(training, session=session)
            
            # Operacja 2: Aktualizuj statystyki użytkownika
            users_col.update_one(
                {"_id": user_id},
                {"$inc": {
                    "stats.total_trainings": 1,
                    "stats.total_calories": calories,
                    "stats.total_minutes": duration
                }},
                session=session
            )
            session.commit_transaction()
```

**Co to robi:**
- `client.start_session()` - rozpoczyna sesję MongoDB
- `session.start_transaction()` - otwiera transakcję
- Wszystkie operacje wykonują się w ramach tej samej sesji
- `session.commit_transaction()` - zatwierdza wszystkie zmiany jednocześnie
- Jeśli wystąpi błąd, wszystkie operacje są automatycznie wycofywane

**Zastosowanie w projekcie:**
- Zapewnia że nowy trening ZAWSZE jest zapisany razem z aktualizacją statystyk
- Chroni przed sytuacją gdy trening się zapisze, ale statystyki nie zostaną zaktualizowane
- Gwarantuje spójność danych między kolekcjami

#### **2. Change Streams**

**DEFINICJA:** Change Streams to mechanizm MongoDB który pozwala aplikacji "nasłuchiwać" zmian w bazie danych w czasie rzeczywistym. Gdy coś się zmieni (nowy dokument, aktualizacja, usunięcie), aplikacja od razu o tym wie bez konieczności ciągłego odpytywania bazy.

**Implementacja w `watch_new_trainings()`:**
```python
def watch_new_trainings():
    with trainings_col.watch([{"$match": {"operationType": "insert"}}]) as stream:
        for change in stream:
            doc = change["fullDocument"]
            log_entry = f'New training: {doc["type"]} by {doc["user_id"]} on {doc["date"]}\n'
            with open("log.txt", "a") as f:
                f.write(log_entry)
```

**Co to robi:**
- `trainings_col.watch()` - rozpoczyna nasłuchiwanie zmian w kolekcji treningów
- `{"$match": {"operationType": "insert"}}` - filtruje tylko operacje dodawania nowych dokumentów
- `for change in stream` - pętla czeka na każdą zmianę
- `change["fullDocument"]` - zawiera cały nowy dokument który został dodany
- Automatycznie zapisuje informację o nowym treningu do pliku log.txt

**Zastosowanie w projekcie:**
- Automatyczne logowanie każdego nowego treningu
- Działa w tle (osobny wątek daemon)
- Można rozszerzyć o powiadomienia znajomych
- Real-time monitoring aktywności użytkowników

#### **3. Zaawansowane Operatory Agregacyjne**

**DEFINICJA:** Operatory agregacyjne w MongoDB pozwalają wykonywać złożone obliczenia i transformacje danych bezpośrednio w bazie danych, bez konieczności pobierania danych do aplikacji. To znacznie przyspiesza przetwarzanie i redukuje transfer danych.

**a) Operator `$function` w `get_cardio_intensity_description()`:**

**Co to robi:** Pozwala wykonać własny kod JavaScript bezpośrednio w MongoDB do obliczenia intensywności treningu cardio.

```python
"$function": {
    "body": """
    function(type, metrics) {
        if (type === 'bieganie' && metrics.distance_km && metrics.duration_min) {
            const kmph = (metrics.distance_km / (metrics.duration_min / 60));
            if (kmph < 7) return 'niskie tempo';
            else if (kmph < 11) return 'umiarkowane tempo';
            else return 'wysokie tempo';
        }
        return 'brak danych';
    }
    """,
    "args": ["$type", "$metrics"],
    "lang": "js"
}
```

**Jak działa:**
- Funkcja JavaScript wykonuje się dla każdego dokumentu treningu
- Oblicza prędkość w km/h na podstawie dystansu i czasu
- Zwraca opis intensywności: "niskie tempo", "umiarkowane tempo", "wysokie tempo"
- Wszystko dzieje się na serwerze MongoDB, nie w aplikacji Python

**b) Operator `$setWindowFields` w `get_training_durations_with_previous()`:**

**Co to robi:** Pozwala porównać każdy trening z poprzednimi treningami tego samego typu, tworząc "okno" danych dla analiz.

```python
"$setWindowFields": {
    "partitionBy": "$type",          # Grupuj po typie treningu
    "sortBy": {"date": 1},           # Sortuj po dacie rosnąco
    "output": {
        "previous_duration": {
            "$shift": {
                "output": "$metrics.duration_min",
                "by": -1                 # Weź wartość z poprzedniego dokumentu
            }
        }
    }
}
```

**Jak działa:**
- `partitionBy: "$type"` - dzieli treningi na grupy (bieganie, siłownia, yoga, etc.)
- `sortBy: {"date": 1}` - sortuje w każdej grupie po dacie
- `$shift: {by: -1}` - dla każdego treningu pobiera czas trwania z poprzedniego treningu tego samego typu
- Wynik: każdy dokument ma dodane pole `previous_duration` z czasem poprzedniego treningu

**Zastosowanie w projekcie:**
- Obliczanie intensywności treningu bezpośrednio w bazie danych
- Porównanie postępów między sesjami tego samego typu
- Dynamiczne raporty bez potrzeby skomplikowanej logiki w aplikacji Python
- Znacznie szybsze niż pobieranie wszystkich danych i obliczanie w aplikacji

---

## Redis - Baza Klucz-Wartość

### **Struktura Kluczy**

#### **1. Streaks (Counters)**
```
user:{user_id}:streak:current    → "5"
user:{user_id}:streak:best       → "12"
```

#### **2. Leaderboardy (Sorted Sets)**
```
leaderboard:calories:2025-W23    → {user_id: calories_score}
```

#### **3. Przypomnienia (Strings z TTL)**
```
reminder:{user_id}:tomorrow      → "Czas na trening!"
```

### **Specyficzne Właściwości Redis**

#### **1. Counters dla Serii**

**DEFINICJA:** Counters (liczniki) w Redis to proste wartości numeryczne które można bardzo szybko zwiększać (INCR) lub zmniejszać (DECR). Idealne do śledzenia rzeczy które zmieniają się często, jak serie treningowe.

**Implementacja w `update_user_streak()`:**
```python
def update_user_streak(user_id):
    # Pobierz aktualną serię
    current_streak = int(redis_client.get(f"user:{user_id}:streak:current") or 0)
    best_streak = int(redis_client.get(f"user:{user_id}:streak:best") or 0)
    
    if yesterday_training:
        new_streak = current_streak + 1  # Kontynuuj serię
    else:
        new_streak = 1  # Rozpocznij nową serię
    
    # Zapisz nową serię
    redis_client.set(f"user:{user_id}:streak:current", new_streak)
    
    # Aktualizuj rekord jeśli potrzeba
    if new_streak > best_streak:
        redis_client.set(f"user:{user_id}:streak:best", new_streak)
```

**Co to robi:**
- `redis_client.get()` - pobiera wartość licznika z Redis (bardzo szybko)
- `redis_client.set()` - zapisuje nową wartość licznika
- Operacje są atomowe - nie ma ryzyka że dwa równoczesne zapisy się pomieszają
- Redis przechowuje tylko aktualną serię i najlepszą serię (2 proste liczby)

**Dlaczego Redis, a nie MongoDB:**
- Redis: 1 operacja GET/SET - czas odpowiedzi < 1ms
- MongoDB: zapytanie, filtrowanie, parsowanie dokumentu - czas odpowiedzi ~10-50ms
- Serie są aktualizowane po każdym treningu (często), więc szybkość ma znaczenie

**Zastosowanie w projekcie:**
- Śledzenie aktualnej serii treningowej użytkownika
- Przechowywanie rekordu osobistego (najdłuższa seria)
- Błyskawiczne aktualizacje po każdym treningu

#### **2. Sorted Sets dla Rankingów**

**DEFINICJA:** Sorted Sets (Zbiory Sortowane) w Redis to struktura danych która automatycznie sortuje elementy według wyniku (score). Każdy element ma przypisaną wartość liczbową i Redis automatycznie utrzymuje sortowanie od najniższej do najwyższej wartości.

**Implementacja w `update_calories_leaderboard()`:**
```python
def update_calories_leaderboard(user_id, calories):
    week_key = get_week_key()  # np. "2025-W23"
    calories_key = f"leaderboard:calories:{week_key}"
    
    # Dodaj kalorie do sumy użytkownika
    redis_client.zincrby(calories_key, calories, user_id)
    
    # Ustaw TTL na 7 dni
    redis_client.expire(calories_key, 604800)
```

**Pobieranie rankingu w `get_calories_leaderboard()`:**
```python
# Pobierz top 10 (od najwyższego)
top_users = redis_client.zrevrange(calories_key, 0, 9, withscores=True)
```

**Co to robi:**
- `zincrby(key, amount, member)` - dodaje `calories` do aktualnej sumy użytkownika w rankingu
- Redis automatycznie sortuje wszystkich użytkowników według łącznej liczby kalorii
- `zrevrange(key, start, stop, withscores=True)` - pobiera top 10 użytkowników od najwyższego wyniku
- `withscores=True` - zwraca też wyniki (liczbę kalorii), nie tylko nazwy użytkowników

**Przykład jak to działa:**
```
Ranking tygodniowy kalorii:
user123: 1500 kcal
user456: 1200 kcal  
user789: 800 kcal

Po dodaniu 300 kcal dla user456:
user123: 1500 kcal
user456: 1500 kcal  # automatycznie przesunięty
user789: 800 kcal
```

**Dlaczego Sorted Sets:**
- Automatyczne sortowanie - nie trzeba sortować w aplikacji
- Dodawanie punktów w czasie O(log N) - bardzo szybko
- Top N w czasie O(log N + N) - błyskawiczne rankingi
- Atomowe operacje - bezpieczne dla wielu użytkowników jednocześnie

**Zastosowanie w projekcie:**
- Ranking spalonych kalorii w aktualnym tygodniu
- Automatyczne utrzymywanie kolejności najlepszych wyników
- Szybkie pobieranie top 10 bez sortowania w aplikacji

#### **3. TTL (Time To Live)**

**DEFINICJA:** TTL to mechanizm automatycznego usuwania danych z Redis po określonym czasie. Gdy ustawimy TTL na klucz, Redis automatycznie go usuwa po upływie tego czasu. Nie trzeba pamiętać o ręcznym sprzątaniu starych danych.

**Implementacja w `set_training_reminder()`:**
```python
def set_training_reminder(user_id):
    reminder_key = f"reminder:{user_id}:tomorrow"
    message = "Czas na trening!"
    
    # Ustaw przypomnienie z TTL 24h
    redis_client.setex(reminder_key, 86400, message)
```

**Sprawdzanie TTL w `get_training_reminder()`:**
```python
if message:
    ttl = redis_client.ttl(reminder_key)  # Pozostały czas w sekundach
    hours_left = ttl // 3600
    return f"{message} (zostało {hours_left} godzin)"
```

**Co to robi:**
- `setex(key, seconds, value)` - ustawia wartość Z AUTOMATYCZNYM wygaśnięciem po 86400 sekundach (24 godziny)
- `ttl(key)` - sprawdza ile sekund zostało do automatycznego usunięcia klucza
- Po 24 godzinach Redis automatycznie usuwa przypomnienie - nie zajmuje już pamięci

**Przykład życia przypomnienia:**
```
Dzisiaj 10:00:  setex() - utworzenie przypomnienia (TTL: 86400s = 24h)
Dzisiaj 15:00:  ttl() zwraca 68400s (19 godzin zostało)
Dzisiaj 20:00:  ttl() zwraca 50400s (14 godzin zostało)  
Jutro 10:00:   ttl() zwraca -2 (klucz nie istnieje - automatycznie usunięty)
```

**TTL w rankingach:**
```python
# Ranking tygodniowy automatycznie się resetuje
redis_client.expire(calories_key, 604800)  # 7 dni = 604800 sekund
```

**Dlaczego TTL jest ważne:**
- **Automatyczne sprzątanie** - stare dane znikają same, nie trzeba o tym pamiętać
- **Oszczędność pamięci** - Redis nie przechowuje nieskończenie danych
- **Resetowanie rankingów** - co tydzień nowy ranking startuje automatycznie
- **Tymczasowe przypomnienia** - znikają gdy nie są już potrzebne

**Zastosowanie w projekcie:**
- Przypomnienia znikają po 24 godzinach
- Rankingi tygodniowe resetują się automatycznie co 7 dni
- Nie trzeba pisać kodu do usuwania starych danych
- Redis pozostaje "czysty" bez nagromadzonych śmieci

### 🔄 **Przepływ Danych Redis**

#### **Po dodaniu treningu:**
1. **Streak:** Aktualizacja liczników serii
2. **Leaderboard:** Dodanie kalorii do rankingu tygodniowego
3. **Reminder:** Ustawienie przypomnienia na jutro

#### **Przykład kluczy dla użytkownika `user123`:**
```
user:user123:streak:current        → "3"      (bez TTL)
user:user123:streak:best           → "7"      (bez TTL)
leaderboard:calories:2025-W23      → sorted set (TTL: 7 dni)
reminder:user123:tomorrow          → "Czas na trening!" (TTL: 24h)
```

---

## **Integracja MongoDB + Redis**

### **Przepływ w funkcji `add_training()`:**

1. **MongoDB Transaction:**
   - Zapisz trening w `trainings` kolekcji
   - Aktualizuj statystyki w `users` kolekcji
   - Commit transakcji

2. **Redis Updates:**
   - Aktualizuj streak counters
   - Dodaj do leaderboard (Sorted Set)
   - Ustaw reminder z TTL

3. **Change Stream:**
   - Automatyczne logowanie nowego treningu
   - Działanie w tle (daemon thread)

### **Zalety Kombinacji:**

**MongoDB:**
- Trwałe przechowywanie złożonych dokumentów
- Transakcje zapewniające spójność
- Zaawansowane agregacje i raporty

**Redis:**
- Błyskawiczne operacje na licznikach
- Automatyczne sortowanie w rankingach
- TTL dla tymczasowych danych
- Minimal memory footprint

---

## **Wydajność i Skalowanie**

### **MongoDB:**
- Replica Set dla wysokiej dostępności
- Change Streams dla reaktywności
- Indeksy na często przeszukiwanych polach

### **Redis:**
- In-memory storage dla maksymalnej szybkości
- Automatyczne wygasanie niepotrzebnych danych
- Atomowe operacje eliminujące race conditions

### **Optymalizacje:**
- Redis przechowuje tylko aktywne dane (streaks, bieżące rankingi)
- MongoDB przechowuje pełną historię i metadata
- TTL zapobiega rozrastaniu się Redis
- Change Streams umożliwiają real-time updates