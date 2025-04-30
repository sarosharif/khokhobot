import datetime
import random
from flask import Flask, request, jsonify, render_template, session
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer
import yaml

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Required for session to work

# Initialize chatbot
kho_kho_bot = ChatBot(
    "KhoKhoBot",
    read_only=True,
    logic_adapters=[
        "chatterbot.logic.BestMatch",
        "chatterbot.logic.MathematicalEvaluation"
    ],
    preprocessors=[
        'chatterbot.preprocessors.clean_whitespace'
    ]
)

# Train on general English corpus
trainer = ChatterBotCorpusTrainer(kho_kho_bot)
trainer.train("chatterbot.corpus.english")

# Train on custom YAML
with open("kho-kho.yaml", "r", encoding="utf-8") as file:
    corpus_data = yaml.safe_load(file)

conversations = corpus_data.get("conversations", [])
list_trainer = ListTrainer(kho_kho_bot)
for convo in conversations:
    if isinstance(convo, list) and all(isinstance(msg, str) for msg in convo):
        list_trainer.train(convo)

# Greeting based on time
def get_greeting():
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 18:
        return "Good afternoon"
    return "Good evening"

@app.route("/")
def index():
    session.clear()  # Reset session on refresh
    initial_message = f"{get_greeting()}! I'm KhoKhoBot, your guide to the exciting game of Kho-Kho. What's your name?"
    return render_template("index.html", initial_message=initial_message)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    user_message_lower = user_message.lower()

    # If name not yet set
    if "name" not in session:
        name = None

        # Check common ways users give their names
        if "my name is" in user_message_lower:
            name = user_message_lower.split("my name is")[-1].strip()
        elif "i am" in user_message_lower:
            name = user_message_lower.split("i am")[-1].strip()
        elif "i'm" in user_message_lower:
            name = user_message_lower.split("i'm")[-1].strip()
        elif "this is" in user_message_lower:
            name = user_message_lower.split("this is")[-1].strip()
        # Fallback: if user types a single word, treat it as name
        elif len(user_message.split()) == 1 and user_message.isalpha():
            name = user_message.strip()

        if name:
            # Use only first word as name and capitalize it
            session["name"] = name.split()[0].capitalize()
            return jsonify({
                "message": f"Nice to meet you, {session['name']}! Ask me anything about Kho-Kho."
            })
        else:
            return jsonify({
                "message": "Hi! May I know your name? You can say 'My name is Sara'."
            })

    # Bot responds normally if name is already known
    bot_reply = kho_kho_bot.get_response(user_message)

    if float(bot_reply.confidence) < 0.4:
        return jsonify({
            "message": f"I'm not sure about that, {session['name']}. Try asking something else about Kho-Kho."
        })

    message_text = str(bot_reply)
    
    # Send video only once per session
    if (
        not session.get("video_sent", False) and
        any(word in user_message_lower for word in ["video", "how to play", "rules", "kho-kho"])
    ):
        session["video_sent"] = True
        return jsonify({
            "message": message_text,
            "video": "/static/kho-kho.mp4"
        })

    return jsonify({"message": message_text})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
