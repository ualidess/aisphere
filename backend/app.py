import os
import tempfile
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

NEW_API_URL = os.getenv("NEW_API_URL")
NEW_API_KEY = os.getenv("NEW_API_KEY")

@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "API is running"})

@app.route("/stt", methods=["POST"])
def stt():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files["audio"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        audio_file.save(tmp.name)
        with open(tmp.name, "rb") as f:
            try:
                transcription = client.audio.transcriptions.create(model="whisper-1", file=f)
                text = transcription.text
            except Exception as e:
                return jsonify({"error": f"Whisper Error: {e}"}), 500
    os.remove(tmp.name)
    print(f"[STT] Transcription: {text}")
    return jsonify({"text": text})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided"}), 400

    payload = {"user_message": question, "session_id": "default_session"}
    headers = {"X-API-Key": NEW_API_KEY, "Content-Type": "application/json"}
    print(f"[CHAT] Sending to new API: {payload}")
    
    try:
        r = requests.post(NEW_API_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        
        response_data = r.json()
        
        answer = response_data.get("bot_response", "Не удалось извлечь ответ из API.")

    except requests.exceptions.RequestException as e:
        print(f"[CHAT] API Request Error: {e}")
        answer = f"Ошибка сети при обращении к API: {e}"
    except Exception as e:
        error_text = r.text if 'r' in locals() else str(e)
        print(f"[CHAT] Error processing API response: {error_text}")
        answer = "Ошибка: " + error_text

    print(f"[CHAT] Answer: {answer}")
    return jsonify({"answer": answer})

@app.route("/tts", methods=["POST"])
def tts():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text to synthesize"}), 400
    try:
        speech_file_path = os.path.join(tempfile.gettempdir(), f"{os.urandom(16).hex()}.mp3")
        with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="alloy",
            input=text,
        ) as response:
            response.stream_to_file(speech_file_path)
        
        print(f"[TTS] File generated: {speech_file_path}")
        return send_file(speech_file_path, mimetype="audio/mpeg", as_attachment=False)
    except Exception as e:
        print(f"[TTS] TTS Error: {e}")
        return jsonify({"error": "Failed to generate speech"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)