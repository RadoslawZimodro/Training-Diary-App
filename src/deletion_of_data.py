from pymongo import MongoClient

# Połączenie z MongoDB
client = MongoClient("mongodb://localhost:27017/?replicaSet=rs0")
db = client["training_diary"]

# Usunięcie wszystkich dokumentów z kolekcji users
db.users.delete_many({})
print("Usunięto użytkowników.")
db.trainings.delete_many({})
print("Usunięto treningi.")
db.friends.delete_many({})
print("Usunięto znajomych.")