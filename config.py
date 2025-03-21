import os

# Configuration de l'application Flask
JWT_SECRET_KEY = "supersecretkey"  # Clé secrète pour JWT (à changer en production)

# Configuration de la base de données MongoDB
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "hori_chatbot"

# Configuration du modèle MentalBERT
MENTALBERT_MODEL_PATH = "data/mentalbert_finetuned"  # Chemin vers le modèle fine-tuné

# Configuration OpenRouter API (DeepSeek)
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = "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"  # clé API
