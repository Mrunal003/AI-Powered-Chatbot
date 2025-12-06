import sqlite3
import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-flash-latest')

app = Flask(__name__)

# Global variable to help Gemini remember context
# In a real app with multiple users, you would use a Dictionary {session_id: history}
chat_history = [] 

# -----------------------------------------------------------------------------
# DATABASE SETUP
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Table 1: SESSIONS (Holds the list of conversations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            timestamp TEXT
        )
    ''')

    # Table 2: MESSAGES (Holds the actual text, linked to a session)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            sender TEXT,  -- 'user' or 'bot'
            content TEXT,
            timestamp TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# HELPER: Get DB Connection
# -----------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# -----------------------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# API 1: Get all previous sessions (For the Sidebar)
@app.route("/get_sessions", methods=["GET"])
def get_sessions():
    conn = get_db_connection()
    # Get all sessions, newest first
    sessions = conn.execute('SELECT * FROM sessions ORDER BY id DESC').fetchall()
    conn.close()
    
    # Convert DB rows to a list of dictionaries
    session_list = [{"id": row["id"], "title": row["title"]} for row in sessions]
    return jsonify(session_list)

# API 2: Load a specific chat (When user clicks sidebar)
@app.route("/load_chat", methods=["POST"])
def load_chat():
    session_id = request.form["session_id"]
    conn = get_db_connection()
    messages = conn.execute('SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC', (session_id,)).fetchall()
    conn.close()
    
    # Rebuild Gemini's memory (chat_history) so it knows the context!
    global chat_history
    chat_history = []
    message_list = []
    
    for msg in messages:
        # Add to frontend list
        message_list.append({"sender": msg["sender"], "content": msg["content"]})
        
        # Add to Gemini's internal memory
        role = "user" if msg["sender"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})

    return jsonify(message_list)

# API 3: Send a message (The main logic)
@app.route("/get_response", methods=["POST"])
def chat():
    user_message = request.form["msg"]
    session_id = request.form.get("session_id") # Might be empty if it's a new chat

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. IF NEW CHAT: Create a new Session in DB first
    if not session_id or session_id == "null":
        # Use first 30 chars of message as title
        title = user_message[:30] + "..." 
        cursor.execute("INSERT INTO sessions (title, timestamp) VALUES (?, ?)", (title, datetime.now()))
        session_id = cursor.lastrowid # Get the ID of the new session
        
        # Clear global history for a fresh start
        global chat_history
        chat_history = []

    # 2. Get AI Response
    try:
        chat_session = model.start_chat(history=chat_history)
        response = chat_session.send_message(user_message)
        bot_reply = response.text
        
        # Update Gemini memory
        chat_history.append({"role": "user", "parts": [user_message]})
        chat_history.append({"role": "model", "parts": [bot_reply]})
        
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        bot_reply = f"Error: Could not connect to AI. Details: {str(e)}"

    # 3. Save BOTH messages to DB linked to the Session ID
    cursor.execute("INSERT INTO messages (session_id, sender, content, timestamp) VALUES (?, ?, ?, ?)", 
                   (session_id, "user", user_message, datetime.now()))
    
    cursor.execute("INSERT INTO messages (session_id, sender, content, timestamp) VALUES (?, ?, ?, ?)", 
                   (session_id, "bot", bot_reply, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return jsonify({"response": bot_reply, "session_id": session_id})

if __name__ == "__main__":
    app.run(debug=True, port=5001)