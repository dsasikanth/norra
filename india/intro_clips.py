"""
Generate the "Talk to Norra" intro clips — one per language.

A short, generic intro ("Hi, I'm Norra, here's what I do") that the website plays
when a visitor picks a language. Pre-recorded = flawless every time, and shows off
the real Sarvam Telugu voice.

  - Indian languages  -> Sarvam (Bulbul v3, voice ritu)   [best Telugu/Indic quality]
  - English / Mandarin / Urdu -> OpenAI TTS                [multilingual]

Run (you need SARVAM_API_KEY + OPENAI_API_KEY in india/.env):
    source .venv/bin/activate
    python intro_clips.py
Outputs mp3/wav into ../aws/intro_assets/  (terraform then hosts them at /intro/...).
"""

import base64
import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

SARVAM_KEY = os.getenv("SARVAM_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
VOICE = os.getenv("SARVAM_VOICE_ID", "ritu")

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "aws", "intro_assets")
os.makedirs(OUT_DIR, exist_ok=True)

# The master script (English). Edit this to change what Norra says.
MASTER = (
    "Hi! I'm Norra, an AI receptionist for local businesses. "
    "I answer every call, day or night. I book appointments, capture every lead, "
    "and speak with your callers in their own language — so you never miss a customer."
)

# Telugu is hand-written so the name stays the soft నోరా and the code-mixing is natural.
TELUGU = (
    "నమస్కారం! నేను నోరా, మీ business కోసం AI receptionist. "
    "నేను ప్రతి call కి day అయినా night అయినా answer చేస్తాను. "
    "Appointments book చేస్తాను, ప్రతి lead capture చేస్తాను, "
    "మీ customers తో వాళ్ళ భాషలోనే మాట్లాడతాను — మీరు ఏ customer ని miss అవ్వరు."
)

# language label -> (engine, code)
LANGS = {
    "English":   ("openai", "en"),
    "Telugu":    ("sarvam", "te-IN"),
    "Hindi":     ("sarvam", "hi-IN"),
    "Tamil":     ("sarvam", "ta-IN"),
    "Kannada":   ("sarvam", "kn-IN"),
    "Malayalam": ("sarvam", "ml-IN"),
    "Punjabi":   ("sarvam", "pa-IN"),
    "Mandarin":  ("openai", "zh"),
    "Urdu":      ("openai", "ur"),
}


def post_json(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={**headers, "Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"\n❌ {url} -> {e.code}: {e.read().decode()[:400]}\n")


def translate(text, language):
    """Translate the master script into `language` via OpenAI (natural, warm, keep 'Norra')."""
    r = post_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content":
                    f"Translate the user's text into {language} for a warm spoken voice-over. "
                    "Keep it natural and conversational, keep the brand name 'Norra', "
                    "and keep common English business words (appointment, lead, business) as-is "
                    "if that's how locals speak. Return ONLY the translation."},
                {"role": "user", "content": text},
            ],
        },
        {"Authorization": f"Bearer {OPENAI_KEY}"},
    )
    return json.load(r)["choices"][0]["message"]["content"].strip()


def sarvam_tts(text, code, path):
    r = post_json(
        "https://api.sarvam.ai/text-to-speech",
        {"text": text, "target_language_code": code, "speaker": VOICE, "model": "bulbul:v3"},
        {"api-subscription-key": SARVAM_KEY},
    )
    audio = base64.b64decode(json.load(r)["audios"][0])
    with open(path, "wb") as f:
        f.write(audio)


def openai_tts(text, path):
    r = post_json(
        "https://api.openai.com/v1/audio/speech",
        {"model": "gpt-4o-mini-tts", "voice": "shimmer", "input": text},
        {"Authorization": f"Bearer {OPENAI_KEY}"},
    )
    with open(path, "wb") as f:
        f.write(r.read())


def main():
    if not SARVAM_KEY or not OPENAI_KEY:
        raise SystemExit("Set SARVAM_API_KEY and OPENAI_API_KEY in india/.env")

    manifest = {}
    for label, (engine, code) in LANGS.items():
        # text for this language
        if label == "English":
            text = MASTER
        elif label == "Telugu":
            text = TELUGU
        else:
            print(f"  translating -> {label} ...")
            text = translate(MASTER, label)

        ext = "wav" if engine == "sarvam" else "mp3"
        fname = f"intro_{label}.{ext}"
        path = os.path.join(OUT_DIR, fname)
        print(f"  synthesizing {label} ({engine}) -> {fname}")
        if engine == "sarvam":
            sarvam_tts(text, code, path)
        else:
            openai_tts(text, path)
        manifest[label] = fname

    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done. {len(manifest)} clips in {OUT_DIR}")
    print("   Listen, then host them with: cd ../aws && terraform apply")


if __name__ == "__main__":
    main()
