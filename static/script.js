let currentSessionId = null; // Keeps track of the active chat ID

// Run this when the page loads
document.addEventListener("DOMContentLoaded", function() {
    loadSessions(); // Load the sidebar list
});

function sendMessage() {
    let inputField = document.getElementById("user-input");
    let messageText = inputField.value;

    if (messageText.trim() === "") return;

    // 1. Show User Message immediately
    addMessageToChat(messageText, "user-message");
    inputField.value = "";

    // 2. Prepare Data (Include Session ID!)
    let formData = new FormData();
    formData.append("msg", messageText);
    if (currentSessionId) {
        formData.append("session_id", currentSessionId);
    }

    // 3. Send to Server
    fetch("/get_response", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 4. Show Bot Response
        addMessageToChat(data.response, "bot-message");

        // 5. If this was a NEW chat, the server sent back a new ID. Save it.
        if (!currentSessionId && data.session_id) {
            currentSessionId = data.session_id;
            loadSessions(); // Refresh sidebar to show the new title
        }
    })
    .catch(error => console.error("Error:", error));
}

// Load the list of old chats into the sidebar
function loadSessions() {
    fetch("/get_sessions")
    .then(response => response.json())
    .then(sessions => {
        let historyList = document.getElementById("history-list");
        historyList.innerHTML = ""; // Clear current list

        sessions.forEach(session => {
            let div = document.createElement("div");
            div.className = "history-item";
            div.innerText = session.title;
            // When clicked, load that specific chat
            div.onclick = () => loadChatHistory(session.id); 
            historyList.appendChild(div);
        });
    });
}

// Load messages for a specific session
function loadChatHistory(sessionId) {
    currentSessionId = sessionId; // Update active ID
    
    // Clear the visual chat box
    let chatBox = document.getElementById("chat-box");
    chatBox.innerHTML = ``; // Clear it completely

    let formData = new FormData();
    formData.append("session_id", sessionId);

    fetch("/load_chat", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(messages => {
        // Re-draw all messages from history
        messages.forEach(msg => {
            let className = (msg.sender === "user") ? "user-message" : "bot-message";
            addMessageToChat(msg.content, className);
        });
    });
}

function startNewChat() {
    currentSessionId = null; // Reset ID
    // Reset visual UI
    document.getElementById("chat-box").innerHTML = `
        <div class="message bot-message">
            <div class="bot-icon">🤖</div>
            <div class="message-content">Hello! I'm your AI Java Tutor. Ready to learn?</div>
        </div>
    `;
}

function addMessageToChat(text, className) {
    let chatBox = document.getElementById("chat-box");
    let messageDiv = document.createElement("div");

    if (className === "user-message") {
        messageDiv.className = "message user-message";
        messageDiv.innerText = text;
    } else {
        messageDiv.className = "message bot-message";
        messageDiv.innerHTML = `<div class="bot-icon">✨</div><div class="message-content">${text}</div>`;
    }

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Enter key support
document.getElementById("user-input").addEventListener("keypress", function(event) {
    if (event.key === "Enter") sendMessage();
});