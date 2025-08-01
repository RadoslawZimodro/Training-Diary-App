import uuid
import json
import random
from datetime import datetime, timedelta

# Generator użytkowników
def generate_users(count):
    first_names = ["janek", "ania", "kasia", "marek", "ola", "bartek", "zosia", "tomek", "gosia", "krzysiek"]
    users = []
    for i in range(count):
        name = random.choice(first_names)
        user = {
            "_id": str(uuid.uuid4()),
            "username": f"{name}{random.randint(100, 999)}",
            "email": f"{name}{i}@example.com",
            "password_hash": f"hashed_password_{i}",
            "age": random.randint(18, 50),
            "gender": random.choice(["male", "female"])
        }
        users.append(user)
    return users

# Typy treningów
activity_types = [
    "siłownia", "bieganie", "pływanie", "rower",
    "yoga", "kalistenika", "trening funkcjonalny"
]

strength_exercises = ["przysiady", "martwy ciąg", "wyciskanie leżąc", "wiosłowanie", "podciąganie"]
calisthenics_exercises = ["pompki", "dipy", "mostek", "podciąganie australijskie"]
functional_exercises = ["kettlebell swing", "burpees", "box jump", "battle rope"]

# Generator treningów
def generate_trainings(user_id, days=12):
    trainings = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        activity_type = random.choice(activity_types)
        entry = {
            "user_id": user_id,
            "date": date.strftime("%Y-%m-%d"),
            "type": activity_type,
            "notes": f"Trening typu {activity_type} w dniu {date.strftime('%d-%m-%Y')}"
        }

        if activity_type == "siłownia":
            entry["metrics"] = {
                "exercises": [
                    {
                        "name": random.choice(strength_exercises),
                        "sets": random.randint(3, 5),
                        "reps": random.randint(6, 12),
                        "weight": random.choice([60, 80, 100, 120])
                    } for _ in range(2)
                ]
            }
        elif activity_type == "bieganie":
            km = round(random.uniform(3, 15), 2)
            minutes = round(km * random.uniform(4.5, 6.5), 2)
            entry["metrics"] = {
                "distance_km": km,
                "duration_min": minutes,
                "calories_burned": random.randint(300, 700)
            }
        elif activity_type == "pływanie":
            entry["metrics"] = {
                "laps": random.randint(10, 40),
                "distance_m": random.randint(500, 2000),
                "stroke": random.choice(["freestyle", "breaststroke", "backstroke"])
            }
        elif activity_type == "rower":
            km = round(random.uniform(5, 40), 2)
            minutes = round(km * random.uniform(2.0, 2.8), 2)
            entry["metrics"] = {
                "distance_km": km,
                "duration_min": minutes
            }
        elif activity_type == "yoga":
            entry["metrics"] = {
                "duration_min": random.randint(30, 90),
                "style": random.choice(["vinyasa", "hatha", "yin"])
            }
        elif activity_type == "kalistenika":
            entry["metrics"] = {
                "exercises": [
                    {
                        "name": random.choice(calisthenics_exercises),
                        "sets": random.randint(2, 5),
                        "reps": random.randint(8, 20)
                    } for _ in range(3)
                ]
            }
        elif activity_type == "trening funkcjonalny":
            entry["metrics"] = {
                "exercises": [
                    {
                        "name": random.choice(functional_exercises),
                        "duration_sec": random.randint(20, 60),
                        "rounds": random.randint(2, 5)
                    } for _ in range(3)
                ]
            }

        trainings.append(entry)
    return trainings

# GENEROWANIE DANYCH
users = generate_users(10)
trainings = []
for user in users:
    trainings.extend(generate_trainings(user["_id"]))

# GENEROWANIE ZNAJOMYCH
def generate_friendships(users):
    friendships = []
    user_ids = [u["_id"] for u in users]
    for user_id in user_ids:
        friends = random.sample([uid for uid in user_ids if uid != user_id], k=random.randint(2, 4))
        friendships.append({
            "user_id": user_id,
            "friends": friends
        })
    return friendships

friend_data = generate_friendships(users)

# ZAPIS DO PLIKÓW
with open("users_10.json", "w", encoding="utf-8") as f:
    json.dump(users, f, indent=2, ensure_ascii=False)

with open("trainings_10_users.json", "w", encoding="utf-8") as f:
    json.dump(trainings, f, indent=2, ensure_ascii=False)

with open("friends.json", "w", encoding="utf-8") as f:
    json.dump(friend_data, f, indent=2, ensure_ascii=False)