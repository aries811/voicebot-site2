import os
import uuid
import asyncio
import aiohttp
import logging
import subprocess
import whisper
from quart import Quart, render_template, request, jsonify
from dotenv import load_dotenv
from pydub import AudioSegment
import webbrowser

# === 🔑 Завантаження .env ===
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ ERROR: GROQ_API_KEY не знайдено в .env")
    exit(1)

GROQ_MODELS = [
    ("LLaMA 3 (8B)", "llama3-8b-8192"),
    ("LLaMA 4 Maverick (17B)", "meta-llama/llama-4-maverick-17b-128e-instruct"),
    ("LLaMA 3 (70B)", "llama3-70b-8192"),
    ("DeepSeek Distill 70B", "deepseek-r1-distill-llama-70b"),
    ("Gemma 2 (9B IT)", "gemma2-9b-it")
]

# === 🧠 Завантаження Whisper ===
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.info("Завантаження Whisper...")
whisper_model = whisper.load_model("base")

# === 🌐 Quart app ===
app = Quart(__name__)

@app.route("/")
async def index():
    return await render_template("index.html", models=GROQ_MODELS)

@app.route("/process_audio", methods=["POST"])
async def process_audio():
    logger.info("▶️ POST /process_audio")

    files = await request.files
    if "audio" not in files:
        return jsonify({"error": "Немає аудіофайлу"}), 400

    file = files["audio"]
    temp_input = f"temp_{uuid.uuid4().hex}.webm"
    temp_output = f"temp_{uuid.uuid4().hex}.wav"

    try:
        await file.save(temp_input)
        audio = AudioSegment.from_file(temp_input)
        if len(audio) < 1000:
            return jsonify({"error": "Аудіо занадто коротке"}), 400

        subprocess.run([
            ffmpeg_path, "-i", temp_input,
            "-ac", "1", "-ar", "16000", temp_output
        ], check=True)

        result = whisper_model.transcribe(temp_output, language="uk")
        user_text = result.get("text", "").strip()

        if not user_text or len(user_text) < 5:
            return jsonify({"error": "Не вдалося розпізнати змістовний текст"}), 400

        form = await request.form
        model_name = form.get("model", GROQ_MODELS[0][0])
        model_id = next((m[1] for m in GROQ_MODELS if m[0] == model_name), GROQ_MODELS[0][1])

        reply = await get_groq_response(user_text, model_id)
        if not reply:
            return jsonify({"error": "Помилка AI"}), 500

        return jsonify({"text": reply})

    finally:
        for f in [temp_input, temp_output]:
            if os.path.exists(f):
                os.remove(f)

@app.route("/process_text", methods=["POST"])
async def process_text():
    form = await request.form
    user_text = form.get("text", "")
    if not user_text:
        return jsonify({"error": "Текст не надіслано"}), 400

    model_name = form.get("model", GROQ_MODELS[0][0])
    model_id = next((m[1] for m in GROQ_MODELS if m[0] == model_name), GROQ_MODELS[0][1])

    reply = await get_groq_response(user_text, model_id)
    if not reply:
        return jsonify({"error": "AI не відповів"}), 500

    return jsonify({"text": reply})

async def get_groq_response(prompt, model, retries=3):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Ти голосовий асистент."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "top_p": 0.9,
        "stream": False
    }

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"].strip()
                    elif response.status in (429, 502, 503):
                        await asyncio.sleep(2 * attempt)
                    else:
                        return None
        except Exception as e:
            logger.error(f"Groq error: {e}")
            await asyncio.sleep(2 * attempt)

    return None

# === ▶️ Запуск сервера ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Взяти порт із оточення або 8080 за замовчуванням
    app.run(host="0.0.0.0", port=port)
