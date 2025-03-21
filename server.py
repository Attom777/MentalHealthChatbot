from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from models import UserManager, ChatbotManager  # On importe UserManager et ChatbotManager depuis models/
from config import JWT_SECRET_KEY  # Importation de la configuration
from datetime import datetime, timezone
from models.rss_manager import RSSManager

# 📌 Initialisation de Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # 🔹 Autorise toutes les origines
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY  # 🔹 Utilisation de la clé JWT depuis config.py
jwt = JWTManager(app)

# 📌 Initialisation des gestionnaires
user_manager = UserManager()
chatbot_manager = ChatbotManager()
rss_manager = RSSManager()

# ----------------------------------------------
# ✅ Authentification
# ----------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    """ Route pour l'inscription d'un utilisateur """
    response, status_code = user_manager.register_user(**request.json)
    return jsonify(response), status_code

@app.route("/login", methods=["POST"])
def login():
    """ Route pour la connexion d'un utilisateur """
    response, status_code = user_manager.login_user(**request.json)
    return jsonify(response), status_code

@app.route("/guest", methods=["POST"])
def guest_login():
    """ Route pour se connecter en mode invité """
    response, status_code = user_manager.guest_login()
    return jsonify(response), status_code

# ----------------------------------------------
# ✅ Gestion des conversations
# ----------------------------------------------
@app.route("/generate_questions", methods=["POST"])
@jwt_required()
def generate_questions():
    """ Génère des questions personnalisées pour un utilisateur """
    user_id = get_jwt_identity()
    response = chatbot_manager.generate_questions(user_id, request.json.get("responses", []))
    return jsonify(response)

# ----------------------------------------------
# ✅ Gestion du chat
# ----------------------------------------------
@app.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    """ Analyse les réponses de l'utilisateur et fournit un diagnostic """
    user_id = get_jwt_identity()
    response = chatbot_manager.analyze_responses(user_id, request.json.get("responses", []))

    # 🔹 Si une erreur est retournée, renvoyer un message d'erreur clair
    if "error" in response:
        return jsonify(response), 500

    return jsonify(response)

# ----------------------------------------------
# ✅ Gestion du quiz
# ----------------------------------------------
@app.route("/quiz", methods=["POST"])
@jwt_required()
def save_quiz():
    """ Enregistre les réponses du quiz de l'utilisateur """
    user_id = get_jwt_identity()
    data = request.json

    # Vérifier si l'utilisateur a déjà répondu aujourd'hui
    today = datetime.now(timezone.utc).date()
    existing_entry = user_manager.get_quiz_entry(user_id, today)

    if existing_entry:
        return jsonify({"message": "Quiz already completed today"}), 400

    # Enregistrer les réponses du quiz
    response = user_manager.save_quiz(user_id, data)
    return jsonify(response)

# ----------------------------------------------
# ✅ Verification du quiz
# ----------------------------------------------
@app.route("/check_quiz", methods=["GET"])
@jwt_required()
def check_quiz():
    """ Vérifie si l'utilisateur a complété le quiz aujourd'hui """
    user_id = get_jwt_identity()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # 🔹 Convertir la date en format string

    existing_entry = user_manager.get_quiz_entry(user_id, today)

    return jsonify({"quiz_completed": bool(existing_entry)})

# ----------------------------------------------
# ✅ Gestion du journal émotionnel
# ----------------------------------------------
@app.route("/dashboard", methods=["GET"])
@jwt_required()
def get_dashboard():
    """
    Retourne l'historique des quiz et des statistiques de conversation
    pour un utilisateur inscrit (non guest).
    """
    user_id = get_jwt_identity()
    
    # Vérifie si c’est un "guest_"
    if user_id.startswith("guest_"):
        return jsonify({"error": "This feature is only available for registered users."}), 403

    # 🔹 Récupérer l'historique des quiz
    quiz_history = user_manager.get_all_quiz_entries(user_id)

    # 🔹 Récupérer les statistiques de conversation
    conversation_stats = chatbot_manager.get_conversation_stats(user_id)

    return jsonify({
        "quiz_history": quiz_history,
        "conversation_stats": conversation_stats
    }), 200

# ----------------------------------------------
# ✅ Historique des conversations
# ----------------------------------------------
@app.route("/conversations", methods=["GET"])
@jwt_required()
def get_conversations():
    """
    Liste les conversations de l'utilisateur (résumé).
    """
    user_id = get_jwt_identity()
    # Vérifier si c’est un "guest_"
    # autoriser ou non l'historique pour un invité.
    if user_id.startswith("guest_"): return jsonify([])

    conv_list = chatbot_manager.list_conversations(user_id)
    return jsonify(conv_list), 200

@app.route("/conversations/<conv_id>", methods=["GET"])
@jwt_required()
def get_conversation_detail(conv_id):
    """
    Renvoie le détail complet d'une conversation (final_responses, diagnosis, etc.)
    """
    user_id = get_jwt_identity()
    # Même logique: pour interdire aux guests:
    if user_id.startswith("guest_"):
        return jsonify({"error": "Guests cannot view conversation history"}), 403

    doc = chatbot_manager.get_conversation_by_id(user_id, conv_id)
    if not doc:
        return jsonify({"error": "Conversation not found"}), 404

    return jsonify(doc), 200

# ----------------------------------------------
# ✅ Gestion des flux RSS
# ----------------------------------------------
@app.route("/feeds", methods=["GET"])
@jwt_required()
def get_feeds():
    """
    Retourne une liste d'articles RSS en fonction du dernier diagnostic
    et du dernier quiz de l'utilisateur.
    """
    user_id = get_jwt_identity()

    # Option: si user_id commence par "guest_", on refuse
    if user_id.startswith("guest_"):
        return jsonify({"error": "RSS feed is available for registered users only."}), 403

    # Récupérer le dernier diagnostic
    recent_conv = chatbot_manager.conversations_collection.find_one(
        {"user_id": user_id, "diagnosis": {"$exists": True}},
        sort=[("timestamp", -1)]
    )
    diagnosis = recent_conv["diagnosis"] if recent_conv else None

    # Récupérer le dernier quiz
    quiz_data = chatbot_manager.get_user_quiz_data(user_id)

    # Construire la liste d’articles
    articles = rss_manager.get_feeds(diagnosis=diagnosis, quiz_data=quiz_data)

    return jsonify({"articles": articles}), 200




# ----------------------------------------------
# 🚀 Démarre le serveur Flask
# ----------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
