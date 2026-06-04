"""
Norra India — simplest possible "hear Telugu" test.
No WebRTC, no microphone, no LLM. Just: text -> Sarvam -> a .wav file you can play.

Use this to confirm your Sarvam key + voice + model work and to HEAR the voice.

    source .venv/bin/activate
    python hear_telugu.py
    open ritu_sample.wav        # plays the audio on macOS
"""

import base64
import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("SARVAM_API_KEY")
VOICE = os.getenv("SARVAM_VOICE_ID", "ritu")          # lowercase, must match the model
MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")    # ritu is a v3 voice

TEXT = (
    "నమస్కారం! సన్‌షైన్ క్లినిక్‌కి కాల్ చేసినందుకు ధన్యవాదాలు. "
    "నేను నోరా. మీకు appointment book చేయాలా, లేదా doctor timings కావాలా?"
)

if not KEY:
    raise SystemExit("SARVAM_API_KEY is not set in .env")

body = json.dumps({
    "text": TEXT,
    "target_language_code": "te-IN",
    "speaker": VOICE,
    "model": MODEL,
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.sarvam.ai/text-to-speech",
    data=body,
    headers={"api-subscription-key": KEY, "Content-Type": "application/json"},
)

try:
    resp = urllib.request.urlopen(req)
    data = json.load(resp)
except urllib.error.HTTPError as e:
    print(f"\n❌ Sarvam API error {e.code}:\n{e.read().decode()}\n")
    print("Common causes: wrong API key, or speaker/model mismatch "
          "(e.g. 'ritu' needs model 'bulbul:v3', not 'bulbul:v2').")
    raise SystemExit(1)

audio = base64.b64decode(data["audios"][0])
out = "ritu_sample.wav"
with open(out, "wb") as f:
    f.write(audio)

print(f"\n✅ Saved {out}  (voice='{VOICE}', model='{MODEL}')")
print(f"   Play it:  open {out}")
