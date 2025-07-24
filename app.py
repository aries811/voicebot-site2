import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

RHVOICE_BINARY = "./RHVoice-client"
DEFAULT_VOICE = "Anna"

@app.route("/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json()
    text = data.get("text")
    voice = data.get("voice", DEFAULT_VOICE)

    if not text:
        return jsonify({"error": "Text is required"}), 400

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            cmd = [RHVOICE_BINARY, "-v", voice, "-o", tmp.name]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            _, err = proc.communicate(input=text.encode("utf-8"))

            if proc.returncode != 0:
                return jsonify({"error": f"RHVoice failed: {err.decode()}"}), 500

            return send_file(tmp.name, mimetype="audio/wav", as_attachment=True, download_name="speech.wav")

    except Exception as e:
        return jsonify({"error": str(e)}), 500