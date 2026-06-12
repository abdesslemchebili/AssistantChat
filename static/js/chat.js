/**
 * AssistantChat — Logique frontend
 *
 * Gère l'envoi des messages, l'affichage de l'historique
 * et la communication avec l'API Flask (/api/chat).
 */

const chatContainer = document.getElementById("chat-container");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");

let isLoading = false;

// --- Chargement de l'historique au démarrage (si session existante) ---
document.addEventListener("DOMContentLoaded", loadHistory);

async function loadHistory() {
    try {
        const response = await fetch("/api/history");
        const data = await response.json();
        if (data.history && data.history.length > 0) {
            clearWelcome();
            data.history.forEach((msg) => appendMessage(msg.role, msg.content));
        }
    } catch (err) {
        console.error("Impossible de charger l'historique :", err);
    }
}

// --- Envoi d'un message ---
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message || isLoading) return;

    clearWelcome();
    appendMessage("human", message);
    userInput.value = "";
    setLoading(true);

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });

        const data = await response.json();

        if (!response.ok) {
            appendMessage("assistant", `Erreur : ${data.error || "Réponse inattendue."}`);
        } else {
            appendMessage("assistant", data.reply);
        }
    } catch (err) {
        appendMessage("assistant", "Erreur réseau. Vérifiez que le serveur Flask est lancé.");
        console.error(err);
    } finally {
        setLoading(false);
        userInput.focus();
    }
});

// --- Réinitialisation de la conversation ---
resetBtn.addEventListener("click", async () => {
    try {
        await fetch("/api/reset", { method: "POST" });
        chatContainer.innerHTML = `
            <div class="welcome-message">
                <p>Bonjour ! Je suis votre assistant voyage. Dites-moi où vous souhaitez aller.</p>
                <p class="hint">Essayez : « Je veux visiter l'Espagne » puis « 800 euros » puis « Propose une autre ville ».</p>
            </div>`;
        userInput.focus();
    } catch (err) {
        console.error("Erreur lors de la réinitialisation :", err);
    }
});

// --- Affichage d'un message dans le chat ---
function appendMessage(role, content) {
    const isUser = role === "human";
    const wrapper = document.createElement("div");
    wrapper.className = `message ${isUser ? "user" : "assistant"}`;

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = isUser ? "Vous" : "Assistant";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = content;

    const inner = document.createElement("div");
    inner.appendChild(label);
    inner.appendChild(bubble);
    wrapper.appendChild(inner);

    chatContainer.appendChild(wrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function clearWelcome() {
    const welcome = chatContainer.querySelector(".welcome-message");
    if (welcome) welcome.remove();
}

function setLoading(loading) {
    isLoading = loading;
    sendBtn.disabled = loading;
    userInput.disabled = loading;

    const existing = chatContainer.querySelector(".typing-indicator");
    if (loading) {
        const indicator = document.createElement("div");
        indicator.className = "typing-indicator";
        indicator.textContent = "L'assistant réfléchit...";
        chatContainer.appendChild(indicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } else if (existing) {
        existing.remove();
    }
}
