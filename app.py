"""
AssistantChat — Atelier éducatif LangChain + LCEL
====================================================

Ce fichier montre comment construire un assistant conversationnel
avec LangChain Expression Language (LCEL) et une interface Flask.

Concepts clés :
  - System Prompt      : définit le rôle et le comportement de l'assistant
  - Conversation Memory: mémorise les échanges précédents
  - LCEL               : assemble Prompt → Modèle → Parser avec l'opérateur |
"""

""" ******************************************************************
groq api key: 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            !!!!!
groq api base: https://api.groq.com/openai/v1                                     !!!!!  
groq model: llama-3.1-8b-instant                                                  !!!!!                  

****************************************************************** """

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session

# --- Imports LangChain ---
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# Chemin absolu vers .env (indépendant du dossier courant du terminal)
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def load_env() -> None:
    """Charge .env depuis le dossier du projet. override=True évite les conflits."""
    load_dotenv(ENV_FILE, override=True)


load_env()

# =============================================================================
# CONFIGURATION DE L'APPLICATION FLASK
# =============================================================================

app = Flask(__name__)
# Clé secrète pour sécuriser les sessions Flask (stockage côté serveur)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "atelier-langchain-demo-secret")

# =============================================================================
# MÉMOIRE DE CONVERSATION (en mémoire vive, sans base de données)
# =============================================================================
#
# Pourquoi la mémoire est utile ?
# Sans mémoire, chaque message serait traité isolément : l'assistant oublierait
# ce que vous avez dit avant. Avec la mémoire, le modèle reçoit l'historique
# complet et peut répondre de façon cohérente sur plusieurs tours.
#
# Structure : { session_id: [ {"role": "human"|"ai", "content": "..."}, ... ] }
# Chaque navigateur reçoit un session_id unique via la session Flask.

conversation_store: dict[str, list[dict[str, str]]] = {}


def get_session_id() -> str:
    """Retourne l'identifiant de session Flask, ou en crée un nouveau."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def get_chat_history(session_id: str) -> list:
    """
    Convertit l'historique stocké en messages LangChain.

    MessagesPlaceholder attend une liste de BaseMessage (HumanMessage, AIMessage).
    C'est ainsi que l'historique est « injecté » dans le prompt avant l'envoi
    au modèle.
    """
    raw_history = conversation_store.get(session_id, [])
    messages = []
    for entry in raw_history:
        if entry["role"] == "human":
            messages.append(HumanMessage(content=entry["content"]))
        elif entry["role"] == "ai":
            messages.append(AIMessage(content=entry["content"]))
    return messages


def save_message(session_id: str, role: str, content: str) -> None:
    """Ajoute un message à l'historique de la session."""
    if session_id not in conversation_store:
        conversation_store[session_id] = []
    conversation_store[session_id].append({"role": role, "content": content})


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
#
# Le System Prompt est le premier message envoyé au modèle. Il définit :
#   - le rôle de l'assistant (ex. assistant voyage)
#   - le ton et le style de réponse
#   - les contraintes (budget, format, etc.)
#
# Le modèle s'appuie sur ce texte pour toute la conversation.

SYSTEM_PROMPT = (
    "You are a helpful travel assistant who suggests budget-friendly trips. "
    "Always consider the user's previously mentioned destination and budget "
    "when making recommendations. Be friendly, concise, and practical. "
    "Respond in the same language the user writes in."
)

# =============================================================================
# CONSTRUCTION DE LA CHAÎNE LCEL
# =============================================================================
#
# LCEL (LangChain Expression Language) permet d'assembler des composants
# avec l'opérateur pipe (|), comme des étapes d'un pipeline :
#
#   Entrée → [Prompt] → [Modèle LLM] → [Parser de sortie] → Texte final
#
# Chaque composant est un « Runnable » : un objet qui accepte une entrée
# et produit une sortie, chaînable avec les autres.

# --- Étape 1 : ChatPromptTemplate ---
# Structure le prompt sous forme de messages de chat.
# MessagesPlaceholder("history") laisse un emplacement dynamique où l'on
# insérera tous les messages précédents (user + assistant) à chaque appel.
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{user_input}"),
    ]
)

# --- Étape 2 & 3 : Modèle + Parser + Chaîne LCEL (initialisation paresseuse) ---
# Le modèle n'est créé qu'au premier appel, pour que Flask démarre même
# si OPENAI_API_KEY n'est pas encore configurée dans le fichier .env.
output_parser = StrOutputParser()
_chain = None
_chain_config: tuple[str | None, str | None, str | None] | None = None


def get_api_key() -> str | None:
    """Lit la clé API (Groq ou OpenAI) depuis les variables d'environnement."""
    load_env()
    key = (os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    return key or None


def get_model_settings() -> tuple[str, str | None, str]:
    """Retourne (api_key, base_url, model_name) pour le fournisseur configuré."""
    load_env()
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Clé API manquante. Ajoutez GROQ_API_KEY ou OPENAI_API_KEY dans le fichier .env."
        )

    base_url = (
        os.getenv("GROQ_API_BASE") or os.getenv("OPENAI_API_BASE") or ""
    ).strip() or None

    if base_url and "groq.com" in base_url:
        default_model = "llama-3.1-8b-instant"
    else:
        default_model = "gpt-4o-mini"

    model_name = (os.getenv("OPENAI_MODEL") or default_model).strip()
    return api_key, base_url, model_name


def get_chain():
    """
    Construit et met en cache la chaîne LCEL : prompt | model | output_parser.

    L'opérateur | assemble les trois étapes :
      1. prompt formate les messages (system + history + nouveau message)
      2. model génère la réponse du LLM
      3. output_parser convertit la réponse en string
    """
    global _chain, _chain_config

    api_key, base_url, model_name = get_model_settings()
    current_config = (api_key, base_url, model_name)

    # Reconstruire la chaîne si .env a changé (ex. passage OpenAI → Groq)
    if _chain is not None and _chain_config == current_config:
        return _chain

    # ChatOpenAI fonctionne avec OpenAI et tout fournisseur compatible
    # (Groq, Ollama, etc.) via OPENAI_API_BASE / GROQ_API_BASE dans .env.
    model = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
    )

    _chain = prompt | model | output_parser
    _chain_config = current_config
    return _chain


# =============================================================================
# ROUTES FLASK
# =============================================================================


@app.route("/")
def index():
    """Affiche la page de chat."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Endpoint API : reçoit un message utilisateur, exécute la chaîne LCEL,
    renvoie la réponse et met à jour la mémoire.
    """
    data = request.get_json()
    user_message = (data or {}).get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Le message ne peut pas être vide."}), 400

    session_id = get_session_id()

    # Récupérer l'historique AVANT d'ajouter le nouveau message
    # (le nouveau message est passé séparément via {user_input})
    history = get_chat_history(session_id)

    try:
        # Invocation de la chaîne LCEL
        # Les clés doivent correspondre aux variables du prompt :
        #   - "history"  → MessagesPlaceholder
        #   - "user_input" → dernier message humain
        assistant_reply = get_chain().invoke(
            {
                "history": history,
                "user_input": user_message,
            }
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        error_msg = str(exc)
        if "401" in error_msg or "invalid_api_key" in error_msg:
            return jsonify(
                {
                    "error": (
                        "Clé API Groq invalide ou mal configurée. "
                        "Vérifiez GROQ_API_KEY dans .env, redémarrez le serveur "
                        "(Ctrl+C puis python app.py), et régénérez la clé sur "
                        "console.groq.com si nécessaire."
                    )
                }
            ), 401
        return jsonify({"error": f"Erreur du modèle : {exc}"}), 500

    # Sauvegarder le message utilisateur et la réponse dans la mémoire
    save_message(session_id, "human", user_message)
    save_message(session_id, "ai", assistant_reply)

    return jsonify(
        {
            "reply": assistant_reply,
            "history": conversation_store[session_id],
        }
    )


@app.route("/api/history", methods=["GET"])
def history():
    """Retourne l'historique complet de la conversation courante."""
    session_id = get_session_id()
    return jsonify({"history": conversation_store.get(session_id, [])})


@app.route("/api/reset", methods=["POST"])
def reset():
    """Efface la mémoire de conversation (utile pour recommencer la démo)."""
    session_id = get_session_id()
    conversation_store[session_id] = []
    return jsonify({"message": "Conversation réinitialisée."})


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    if not get_api_key():
        print("\n⚠️  Clé API non définie.")
        print(f"   Éditez le fichier : {ENV_FILE}")
        print("   Ajoutez : GROQ_API_KEY=gsk_...")
        print("   Relancez : python app.py\n")
    else:
        _, base_url, model_name = get_model_settings()
        provider = "Groq" if base_url and "groq.com" in base_url else "OpenAI"
        print(f"✓ {provider} configuré ({model_name})")
        print("  Serveur prêt sur http://127.0.0.1:5000\n")

    app.run(debug=True, port=5000)
