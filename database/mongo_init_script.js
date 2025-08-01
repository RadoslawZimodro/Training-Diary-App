// Inicjalizacja MongoDB dla Training Diary
// Ten skrypt uruchomi się automatycznie przy pierwszym starcie kontenera

// Przełącz na bazę training_diary
db = db.getSiblingDB('training_diary');

// Stwórz kolekcje z podstawową walidacją
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["username", "email", "password_hash"],
      properties: {
        username: {
          bsonType: "string",
          description: "Username must be a string and is required"
        },
        email: {
          bsonType: "string",
          pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
          description: "Email must be a valid email address"
        },
        password_hash: {
          bsonType: "string",
          description: "Password hash must be a string and is required"
        },
        age: {
          bsonType: "int",
          minimum: 13,
          maximum: 120,
          description: "Age must be an integer between 13 and 120"
        },
        gender: {
          bsonType: "string",
          enum: ["male", "female", "other"],
          description: "Gender must be male, female, or other"
        }
      }
    }
  }
});

db.createCollection("trainings", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "date", "type"],
      properties: {
        user_id: {
          bsonType: "string",
          description: "User ID must be a string and is required"
        },
        date: {
          bsonType: "string",
          description: "Date must be a string and is required"
        },
        type: {
          bsonType: "string",
          enum: ["siłownia", "bieganie", "pływanie", "rower", "yoga", "kalistenika", "trening funkcjonalny"],
          description: "Type must be one of the allowed training types"
        },
        metrics: {
          bsonType: "object",
          description: "Metrics must be an object"
        }
      }
    }
  }
});

db.createCollection("friends");

// Stwórz indeksy dla lepszej wydajności
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.trainings.createIndex({ "user_id": 1, "date": -1 });
db.trainings.createIndex({ "type": 1 });
db.friends.createIndex({ "user_id": 1 });

print("MongoDB initialization completed for Training Diary!");