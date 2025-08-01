from pymongo import MongoClient
import json

# Połączenie z lokalną bazą MongoDB
client = MongoClient("mongodb://127.0.0.1:27017/?replicaSet=rs0")
db = client["training_diary"]

# === USERS ===
with open("users_10.json", encoding="utf-8") as f:
    users = json.load(f)

db.users.delete_many({})
db.users.insert_many(users)
print("Załadowano użytkowników.")

# === TRAININGS ===
with open("trainings_10_users.json", encoding="utf-8") as f:
    trainings = json.load(f)

db.trainings.delete_many({})
db.trainings.insert_many(trainings)
print("Załadowano treningi.")

# === FRIENDS === 
with open("friends.json", encoding="utf-8") as f:
    friends_data = json.load(f)

db.friends.delete_many({})
db.friends.insert_many(friends_data)
print("Załadowano znajomych do kolekcji friends.")