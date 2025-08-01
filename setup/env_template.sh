# Training Diary - Environment Variables
# Skopiuj ten plik do .env i dostosuj wartości do swoich potrzeb

# MongoDB Configuration
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=admin123
MONGODB_DATABASE=training_diary
MONGODB_REPLICA_SET=rs0
MONGODB_CONNECTION_STRING=mongodb://admin:admin123@localhost:27017/training_diary?replicaSet=rs0

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis123
REDIS_DB=0
REDIS_CONNECTION_STRING=redis://:redis123@localhost:6379/0

# Application Settings
APP_DEBUG=True
APP_LOG_LEVEL=INFO

# Future Features
ENABLE_NOTIFICATIONS=False
ENABLE_REAL_TIME_FEATURES=False

# Security (dla przyszłego API)
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# Third-party integrations (dla przyszłych funkcji)
# STRAVA_CLIENT_ID=
# STRAVA_CLIENT_SECRET=
# FITBIT_CLIENT_ID=
# FITBIT_CLIENT_SECRET=