# AssistantChat — Atelier LangChain + LCEL

Projet éducatif pour apprendre à construire un **assistant conversationnel** avec [LangChain](https://python.langchain.com/) et **LCEL** (LangChain Expression Language).

L'objectif est la **compréhension** : le code est volontairement simple, commenté et sans architecture complexe.

---

## Ce que vous allez apprendre

| Concept | Description |
|---------|-------------|
| **System Prompt** | Message système qui définit le rôle de l'assistant (ici : assistant voyage économique). |
| **Conversation Memory** | Stockage des messages précédents pour que l'assistant se souvienne du contexte. |
| **MessagesPlaceholder** | Emplacement dynamique dans le prompt où l'historique est injecté. |
| **LCEL** | Assemblage de composants avec `\|` : `Prompt → Modèle → Parser`. |

---

## Structure du projet

```
AssistantChat/
├── app.py                 # Application Flask + chaîne LCEL
├── requirements.txt       # Dépendances Python
├── .env.example           # Modèle de configuration (clé API)
├── templates/
│   └── index.html         # Page web du chat
├── static/
│   ├── css/
│   │   └── style.css      # Styles de l'interface
│   └── js/
│       └── chat.js        # Logique frontend (envoi, affichage)
└── README.md              # Ce fichier
```

### Rôle de chaque fichier

- **`app.py`** — Cœur du projet. Configure le System Prompt, construit la chaîne LCEL (`ChatPromptTemplate | ChatOpenAI | StrOutputParser`), gère la mémoire en mémoire vive et expose les routes API Flask.
- **`templates/index.html`** — Interface de chat : zone de messages, champ de saisie, bouton d'envoi.
- **`static/css/style.css`** — Mise en page moderne : messages utilisateur à droite (bleu), assistant à gauche (gris foncé).
- **`static/js/chat.js`** — Envoie les messages à `/api/chat`, affiche l'historique, gère le chargement et la réinitialisation.
- **`requirements.txt`** — Liste des paquets Python à installer.
- **`.env.example`** — Variables d'environnement à copier vers `.env`.

---

## Installation et lancement

### Prérequis

- Python 3.10 ou supérieur
- Une clé API compatible OpenAI (OpenAI, Groq, Ollama, etc.)

### Étapes

```bash
# 1. Aller dans le dossier du projet
cd AssistantChat

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la clé API
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
# Puis éditez .env et renseignez OPENAI_API_KEY

# 5. Lancer le serveur
python app.py
```

Ouvrez votre navigateur sur **http://127.0.0.1:5000**.

---

## Comment fonctionne la chaîne LCEL ?

```
Entrée utilisateur + Historique
         │
         ▼
┌─────────────────────────┐
│   ChatPromptTemplate    │  ← System Prompt + MessagesPlaceholder + message actuel
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│      ChatOpenAI         │  ← Appel au modèle de langage
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│    StrOutputParser      │  ← Extraction du texte de réponse
└─────────────────────────┘
         │
         ▼
    Réponse texte
```

Dans `app.py`, la chaîne est définie en une ligne :

```python
chain = prompt | model | output_parser
```

À chaque message, Flask :
1. Récupère l'historique de la session.
2. Appelle `chain.invoke({"history": ..., "user_input": ...})`.
3. Sauvegarde le nouveau message et la réponse dans la mémoire.

---

## Scénario de démo : tester la mémoire

Suivez cette conversation pour vérifier que l'assistant **se souvient du contexte** :

| Tour | Vous écrivez | Ce que l'assistant devrait faire |
|------|--------------|----------------------------------|
| 1 | `Je veux visiter l'Espagne.` | Demander votre budget ou proposer des idées en Espagne. |
| 2 | `800 euros.` | Tenir compte de l'Espagne **et** du budget de 800 €. |
| 3 | `Propose une autre ville.` | Suggérer une **autre ville en Espagne** avec un budget d'**800 €** — sans que vous ayez à répéter ces informations. |

Si l'assistant mentionne l'Espagne et les 800 € au tour 3, la mémoire fonctionne correctement.

Cliquez sur **Nouvelle conversation** pour effacer l'historique et recommencer.

---

## Utiliser un autre fournisseur de modèle

`ChatOpenAI` accepte toute API compatible OpenAI. Modifiez votre `.env` :

```env
# Exemple avec Ollama (local)
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3

# Exemple avec Groq
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk-votre-cle-groq
OPENAI_MODEL=llama-3.1-8b-instant
```

---

## API REST (pour le frontend)

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/` | Page de chat |
| `POST` | `/api/chat` | Envoyer un message (`{"message": "..."}`) |
| `GET` | `/api/history` | Récupérer l'historique de la session |
| `POST` | `/api/reset` | Effacer la mémoire de conversation |

---

## Limites volontaires (pédagogie)

- **Pas de base de données** : la mémoire est en RAM ; elle disparaît au redémarrage du serveur.
- **Pas d'authentification** : une session Flask par navigateur suffit pour l'atelier.
- **Pas d'abstractions avancées** : pas de `RunnableWithMessageHistory` ici, pour que l'injection manuelle de l'historique reste visible et compréhensible.

---

## Ressources pour aller plus loin

- [Documentation LangChain — LCEL](https://python.langchain.com/docs/concepts/lcel/)
- [ChatPromptTemplate](https://python.langchain.com/docs/concepts/prompt_templates/)
- [MessagesPlaceholder](https://python.langchain.com/api_reference/core/prompts/langchain_core.prompts.chat.MessagesPlaceholder.html)

---

Bon atelier !
