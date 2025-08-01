from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import redis
from datetime import datetime, timedelta
# === DB SETUP ===
client = MongoClient("mongodb://localhost:27017/?replicaSet=rs0")
db = client["training_diary"]
users_col = db["users"]
trainings_col = db["trainings"]
friends_col = db["friends"]

# === USER REGISTRATION ===
def register_user(username, email, password, age, gender):
    if users_col.find_one({"username": username}):
        return False
    user = {
        "username": username,
        "email": email,
        "password_hash": password,
        "age": age,
        "gender": gender,
        "stats": {
            "total_trainings": 0,
            "total_calories": 0,
            "total_minutes": 0
        }
    }
    users_col.insert_one(user)
    return True
# ===Połączenie Redis===
try:
    redis_client = redis.Redis(host='localhost', port=6379, password='redis123', decode_responses=True)
    redis_client.ping()  # Test połączenia
    print("Redis połączony!")
except:
    print("Błąd połączenia z Redis")
    redis_client = None

# === USER LOGIN ===
def login_user(email, password):
    user = users_col.find_one({"email": email, "password_hash": password})
    if user:
        return user["_id"]
    return None

# === ADD TRAINING WITH TRANSACTION ===
def add_training(user_id, training):
    with client.start_session() as session:
        with session.start_transaction():
            training["user_id"] = user_id
            trainings_col.insert_one(training, session=session)

            calories = training["metrics"].get("calories_burned", 0)
            duration = training["metrics"].get("duration_min", 0)

            users_col.update_one(
                {"_id": user_id}, # POPRAWKA  2025-06-04
                {
                    "$inc": {
                        "stats.total_trainings": 1,
                        "stats.total_calories": calories,
                        "stats.total_minutes": duration
                    }
                },
                session=session
            )
            # Aktualizuj streak po dodaniu treningu
            session.commit_transaction()
            
    # Aktualizuj streak po zakończeniu transakcji
    new_streak = update_user_streak(user_id,training)
    print(f"Seria treningowa: {new_streak} dni!")
    # Aktualizuj ranking kalorii (tylko jeśli trening ma kalorie)
    if calories > 0:
        update_calories_leaderboard(user_id, calories)
        
        # Sprawdź pozycję użytkownika w rankingu
        position_data = get_user_calories_position(user_id)
        if position_data and position_data["position"]:
            print(f"Ranking kalorii: #{position_data['position']} miejsce ({position_data['calories']} kcal w tym tygodniu)")
    # Ustaw przypomnienie na jutro
    set_training_reminder(user_id)

# === VIEW TRAININGS ===
def view_trainings(user_id):
    results = trainings_col.find({"user_id": user_id})
    for r in results:
        print(r)

# === GET STATS ===
def get_user_stats(user_id):
    user = users_col.find_one({"_id": user_id})
    return user.get("stats", {})
    
# === ADD FRIEND ===    
def add_friend_by_username(user_id, friend_username):
    friend = users_col.find_one({"username": friend_username})
    if not friend:
        return False
    friend_id = friend["_id"]
    if user_id == friend_id:
        return False
    
    # Sprawdź czy już są znajomymi
    user_friends = friends_col.find_one({"user_id": user_id})
    if user_friends and friend_id in user_friends.get("friends", []):
        return False
    
    # Dodaj znajomego do listy użytkownika (lub utwórz listę)
    friends_col.update_one(
        {"user_id": user_id},
        {"$addToSet": {"friends": friend_id}},
        upsert=True
    )
    
    # Dodaj użytkownika do listy znajomego (obustronnie)
    friends_col.update_one(
        {"user_id": friend_id},
        {"$addToSet": {"friends": user_id}},
        upsert=True
    )
    
    return True
# === LIST FRIENDS ===
def list_friends(user_id):
    # Znajdź dokument znajomych dla użytkownika
    friends_doc = friends_col.find_one({"user_id": user_id})
    if not friends_doc or "friends" not in friends_doc:
        return []
    
    friend_ids = friends_doc["friends"]
    return list(users_col.find({"_id": {"$in": friend_ids}}, {"username": 1}))

# === INTENSITY DESCRIPTION FUNCTION ===
def get_cardio_intensity_description(user_id):
    pipeline = [
        {"$match": {"user_id": user_id, "type": {"$in": ["bieganie", "rower", "pływanie"]}}},
        {"$addFields": {
            "intensity_description": {
                "$function": {
                    "body": """
                    function(type, metrics) {
                        if (!metrics || !type) return null;
                        if (type === 'bieganie' && metrics.distance_km && metrics.duration_min) {
                            const kmph = (metrics.distance_km / (metrics.duration_min / 60));
                            if (kmph < 7) return 'niskie tempo';
                            else if (kmph < 11) return 'umiarkowane tempo';
                            else return 'wysokie tempo';
                        }
                        if (type === 'rower' && metrics.avg_speed_kmh) {
                            if (metrics.avg_speed_kmh < 15) return 'wolna jazda';
                            else if (metrics.avg_speed_kmh < 25) return 'umiarkowane tempo';
                            else return 'szybka jazda';
                        }
                        if (type === 'pływanie' && metrics.laps && metrics.pool_length_m && metrics.duration_min) {
                            const mpm = (metrics.laps * metrics.pool_length_m) / metrics.duration_min;
                            if (mpm < 15) return 'spokojne tempo';
                            else if (mpm < 30) return 'średnie tempo';
                            else return 'intensywne pływanie';
                        }
                        return 'brak danych';
                    }
                    """,
                    "args": ["$type", "$metrics"],
                    "lang": "js"
                }
            }
        }}
    ]
    return list(trainings_col.aggregate(pipeline))

# === WINDOW FIELD AGGREGATION ===
def get_training_durations_with_previous(user_id):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$setWindowFields": {
            "partitionBy": "$type",
            "sortBy": {"date": 1},
            "output": {
                "previous_duration": {
                    "$shift": {
                        "output": "$metrics.duration_min",
                        "by": -1
                    }
                }
            }
        }}
    ]
    return list(trainings_col.aggregate(pipeline))

# === COMPARE TRAININGS ===
def compare_last_training_with_previous_three(user_id):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$sort": {"date": -1}},
        {"$limit": 4}
    ]
    trainings = list(trainings_col.aggregate(pipeline))
    if len(trainings) < 2:
        print("Za mało danych do porównania.")
        return

    last = trainings[0]
    previous = trainings[1:]
    print(f"\nOstatni trening: {last['type']}, {last['metrics'].get('duration_min', 0)} min, {last['metrics'].get('calories_burned', 0)} kcal")
    print("Poprzednie 3 treningi:")
    for t in previous:
        # date jest stringiem, nie datetime - użyj bezpośrednio
        print(f"- {t['type']} | {t['date']} | {t['metrics'].get('duration_min', 0)} min | {t['metrics'].get('calories_burned', 0)} kcal")
        
# === WATCH CHANGE STREAM ===
def watch_new_trainings():
    with trainings_col.watch([{"$match": {"operationType": "insert"}}]) as stream:
        print("Change stream listening for new trainings...")
        for change in stream:
            doc = change["fullDocument"]
            log_entry = f'New training: {doc["type"]} by {doc["user_id"]} on {doc["date"]}\n'
            with open("log.txt", "a") as f:
                f.write(log_entry)
            print(log_entry.strip())

# === MENU ===
def get_user_streak(user_id):
    """Pobierz aktualną serię użytkownika"""
    if not redis_client:
        return {"current": 0, "best": 0}
        
    user_id_str = str(user_id)
    current = redis_client.get(f"user:{user_id_str}:streak:current") or 0
    best = redis_client.get(f"user:{user_id_str}:streak:best") or 0
    
    return {
        "current": int(current),
        "best": int(best)
    }

def update_user_streak(user_id,training):
    """Aktualizuj serię po dodaniu treningu"""
    if not redis_client:
        return
    user_id_str = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Sprawdź czy użytkownik trenował wczoraj
    yesterday_training = trainings_col.find_one({
        "user_id": user_id,
        "date": yesterday
    })
    
    # Pobierz aktualną serię
    current_streak = int(redis_client.get(f"user:{user_id_str}:streak:current") or 0)
    best_streak = int(redis_client.get(f"user:{user_id_str}:streak:best") or 0)
    
    last_training_day = redis_client.get(f"user:{user_id_str}:streak:last_day")
    training_date = training["date"]  # Data dodawanego treningu

    if last_training_day == training_date:
        # Już trenował w tym dniu
        return current_streak
    elif last_training_day:
        # Sprawdź czy to kontynuacja serii (dzień po ostatnim treningu)
        last_date = datetime.strptime(last_training_day, "%Y-%m-%d")
        current_date = datetime.strptime(training_date, "%Y-%m-%d")
        if (current_date - last_date).days == 1:
            # Kontynuuj serię
            new_streak = current_streak + 1
        else:
            # Przerwa w serii lub trening wstecz
            new_streak = 1
    else:
        # Pierwszy trening
        new_streak = 1

    # Zapisz datę treningu (nie dzisiejszą datę!)
    redis_client.set(f"user:{user_id_str}:streak:last_day", training_date)
    
    # Zapisz nową serię
    redis_client.set(f"user:{user_id_str}:streak:current", new_streak)
    
    # Aktualizuj najlepszą serię jeśli potrzeba
    if new_streak > best_streak:
        redis_client.set(f"user:{user_id_str}:streak:best", new_streak)
        print(f"NOWY REKORD! Seria {new_streak} dni!")
    
    return new_streak

def display_user_streak(user_id):
    """Wyświetl informacje o serii użytkownika"""
    if not redis_client:
        print("Redis niedostępny - streaks nie działają")
        return
    user_id_str = str(user_id)
    streak_data = get_user_streak(user_id)
    current = streak_data["current"]
    best = streak_data["best"]
    
    print(f"\nTWOJA SERIA TRENINGOWA:")
    print(f"Aktualna seria: {current} dni")
    print(f"Najlepsza seria: {best} dni")
    
    if current == 0:
        print("Dodaj trening aby rozpocząć serię!")
    elif current == 1:
        print("Świetny start! Kontynuuj jutro!")
    elif current >= 7:
        print("NIESAMOWITE! Tygodniowa seria!")
    elif current >= 30:
        print("LEGENDA! Miesięczna seria!")
    else:
        print(f"Świetnie! Jeszcze {7-current} dni do tygodniowej serii!")
def get_week_key():
    """Generuj klucz dla aktualnego tygodnia (format: 2025-W23)"""
    today = datetime.now()
    week = today.isocalendar()[1]  # Numer tygodnia w roku
    year = today.year
    return f"{year}-W{week:02d}"

def update_calories_leaderboard(user_id, calories):
    """Dodaj kalorie do rankingu tygodniowego"""
    if not redis_client:
        return
    user_id_str = str(user_id)
    week_key = get_week_key()
    calories_key = f"leaderboard:calories:{week_key}"
    # Dodaj kalorie do aktualnej sumy użytkownika
    redis_client.zincrby(calories_key, calories, user_id_str)
    
    # Ustaw TTL na 7 dni (ranking resetuje się co tydzień)
    redis_client.expire(calories_key, 604800)  # 604800 sekund = 7 dni
    
def set_training_reminder(user_id):
    """Ustaw przypomnienie o treningu na jutro"""
    if not redis_client:
        return
    user_id_str = str(user_id)
    reminder_key = f"reminder:{user_id_str}:tomorrow"
    message = "Czas na trening!"
    
    # Przypomnienie na 24 godziny
    redis_client.setex(reminder_key, 86400, message)

def get_training_reminder(user_id):
    """Sprawdź czy użytkownik ma przypomnienie"""
    if not redis_client:
        return None
    user_id_str = str(user_id)
    reminder_key = f"reminder:{user_id_str}:tomorrow"
    message = redis_client.get(reminder_key)
    
    if message:
        # Sprawdź ile godzin zostało
        ttl = redis_client.ttl(reminder_key)
        hours_left = ttl // 3600
        return f"{message} (zostało {hours_left} godzin)"
    
    return None

def display_training_reminder(user_id):
    """Wyświetl przypomnienie użytkownika"""
    print("\n=== TWOJE PRZYPOMNIENIE ===")
    
    reminder = get_training_reminder(user_id)
    
    if reminder:
        print(f"• {reminder}")
    else:
        print("Brak przypomnienia")
        print("Dodaj trening aby ustawić przypomnienie na jutro!")

def get_calories_leaderboard():
    """Pobierz top 10 ranking spalonych kalorii"""
    if not redis_client:
        return []
    week_key = get_week_key()
    calories_key = f"leaderboard:calories:{week_key}"
    
    # Pobierz top 10 z wynikami (zrevrange(od najwyższego))
    top_users = redis_client.zrevrange(calories_key, 0, 9, withscores=True)
    
    # Konwertuj na czytelną listę z nazwami użytkowników
    leaderboard = []
    for i, (user_id, calories) in enumerate(top_users, 1):
        user = users_col.find_one({"_id": user_id})
        username = user["username"] if user else "Nieznany"
        leaderboard.append({
            "position": i,
            "username": username,
            "calories": int(calories)
        })
    
    return leaderboard

def get_user_calories_position(user_id):
    """Sprawdź pozycję użytkownika w rankingu kalorii"""
    if not redis_client:
        return None
    user_id_str = str(user_id)
    week_key = get_week_key()
    calories_key = f"leaderboard:calories:{week_key}"
    
    # Pobierz pozycję (rank) i wynik (score)
    position = redis_client.zrevrank(calories_key, user_id_str)
    score = redis_client.zscore(calories_key, user_id_str)
    
    return {
        "position": (position + 1) if position is not None else None,
        "calories": int(score) if score else 0
    }

def display_calories_leaderboard():
    """Wyświetl ranking spalonych kalorii"""
    if not redis_client:
        print("Redis niedostępny - ranking nie działa")
        return
    week_key = get_week_key()
    print(f"\nRANKING KALORII - TYDZIEN {week_key}")
    print("=" * 40)
    
    leaderboard = get_calories_leaderboard()
    
    if leaderboard:
        for entry in leaderboard:
            print(f"{entry['position']}. {entry['username']} - {entry['calories']} kcal")
    else:
        print("Brak danych w tym tygodniu")
        print("Dodaj trening z kaloriami aby pojawic sie w rankingu!")
def main_menu(user_id):
    while True:
        print("\n=== MENU TRENINGOWE ===")
        print("1. Dodaj trening")
        print("2. Wyświetl treningi")
        print("3. Statystyki")
        print("4. Dodaj znajomego po nazwie użytkownika")
        print("5. Wyświetl znajomych")
        print("6. Opis intensywności cardio")
        print("7. Porównaj ostatni trening z trzema poprzednimi")
        print("8. Sprawdź serię treningową")
        print("9. Zobacz ranking kalorii")
        print("10. Sprawdź przypomnienie")
        print("11. Porównaj czas trwania z poprzednim treningiem (wg typu)")
        print("0. Wyloguj")

        choice = input("Choose: ")

        if choice == "1":
            training_type = input("Typ: ")
            date = input("Data (RRRR-MM-DD): ")
            duration = int(input("Czas trwania (min): "))
            calories = int(input("Kalorie: "))

            metrics = {
                "duration_min": duration,
                "calories_burned": calories
            }

            if training_type == "bieganie":
                metrics["distance_km"] = float(input("Dystans (km): "))
            elif training_type == "rower":
                metrics["avg_speed_kmh"] = float(input("Średnia prędkość (km/h): "))
            elif training_type == "pływanie":
                metrics["laps"] = int(input("Długości basenu: "))
                metrics["pool_length_m"] = int(input("Długość basenu (m): "))
            elif training_type == "kalistenika":
                metrics["exercises"] = input("Ćwiczenia (oddzielone przecinkami): ").split(",")

            training = {
                "type": training_type,
                "date": date,
                "metrics": metrics
            }

            add_training(user_id, training)
            print("Trening dodany.")

        elif choice == "2":
            view_trainings(user_id)
        elif choice == "3":
            print(get_user_stats(user_id))
        elif choice == "4":
            fuser = input("Nazwa znajomego: ")
            print("Znajomy dodany!" if add_friend_by_username(user_id, fuser) else "Błąd.")
        elif choice == "5":
            for u in list_friends(user_id):
                print("-", u["username"])
        elif choice == "6":
            for r in get_cardio_intensity_description(user_id):
                print(f'{r["type"]} – {r.get("intensity_description")}')
        elif choice == "7":
            compare_last_training_with_previous_three(user_id)
        elif choice == "8":
            display_user_streak(user_id)    
        elif choice == "9": 
            display_calories_leaderboard()
        elif choice == "10":
            display_training_reminder(user_id)
        elif choice == "11":
            result = get_training_durations_with_previous(user_id)

            # Słownik: {typ_treningu: ostatni_trening}
            latest_by_type = {}

            for r in result:
                t_type = r.get("type")
                curr_date = r.get("date")
                if not t_type or not curr_date:
                    continue
                if t_type not in latest_by_type or curr_date > latest_by_type[t_type]["date"]:
                    latest_by_type[t_type] = r

            print("\n=== Ostatni trening każdego typu + porównanie ===")
            for t_type, training in latest_by_type.items():
                curr_dur = training.get("metrics", {}).get("duration_min", 0)
                prev_dur = training.get("previous_duration")
                if prev_dur is not None:
                    diff = curr_dur - prev_dur
                    trend = f"(+{diff} min)" if diff > 0 else f"({diff} min)" if diff < 0 else "(bez zmian)"
                    print(f"{t_type}: {curr_dur} min, poprzedni {prev_dur} min {trend}")
                else:
                    print(f"{t_type}: {curr_dur} min, brak wcześniejszego treningu")
        elif choice == "0":
            break
        
# === APP START ===
def start():
    print("=== Training Diary App ===")
    while True:
        print("\n1. Zaloguj się")
        print("2. Zarejestruj się")
        print("0. Zakończ")
        opt = input("Wybierz opcję: ")

        if opt == "1":
            email = input("Email: ")
            pw = input("Hasło: ")
            uid = login_user(email, pw)
            if uid:
                main_menu(uid)
            else:
                print("Niepoprawne dane logowania.")
        elif opt == "2":
            un = input("Username: ")
            em = input("Email: ")
            pw = input("Hasło: ")
            age = int(input("Age: "))
            gen = input("Gender: ")
            print("Zarejestrowano." if register_user(un, em, pw, age, gen) else "Nazwa użytkownika już zajęta.")
        elif opt == "0":
            break

if __name__ == "__main__":
    from threading import Thread
    Thread(target=watch_new_trainings, daemon=True).start()
    start()