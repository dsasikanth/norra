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
    "Hi! I'm Nora, the AI receptionist from Norra. I answer your phone 24/7 — "
    "booking appointments, capturing every lead, and speaking with your customers "
    "in their own language, so you never miss a call. "
    "You can try me free for 30 days. Want to see what I can do for your business?"
)

# Telugu is hand-written so the name stays the soft నోరా and the code-mixing is natural.
TELUGU = (
    "నమస్కారం! నేను Nora, మీ AI receptionist. "
    "నేను మీ phone కి 24/7 answer చేస్తాను — appointments book చేస్తాను, "
    "ప్రతి lead capture చేస్తాను, మీ customers తో వాళ్ళ భాషలోనే మాట్లాడతాను. "
    "మీరు ఏ call ని miss అవ్వరు. 30 రోజులు free గా try చేయండి. "
    "మీ business కోసం నేను ఏం చేయగలనో చూద్దామా?"
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


# Short spoken answers to the questions a business owner asks. Served from S3 — instant, free.
FAQ = {
    "what": "Norra is an AI receptionist that answers your business phone 24 by 7 — booking "
            "appointments, capturing every lead, and speaking your customers' language, so you "
            "never miss a call.",
    "how": "We set everything up for you. We connect a number, or forward your existing one, to "
           "Norra. It learns your business and answers every call in your style, and sends booking "
           "confirmations on WhatsApp.",
    "trial": "Yes — Norra is free for 30 days, up to 200 minutes, with full setup included, and you "
             "can cancel anytime. You hear Norra answer your real calls before paying anything.",
    "pricing": "After the free trial, plans start at 2,500 rupees a month for 300 minutes, 6,000 "
               "rupees for 1,000 minutes, and 12,000 rupees for larger clinics. Most businesses "
               "never exceed their plan.",
    "languages": "Norra speaks Telugu, Hindi, English, Tamil, Kannada, Malayalam and more, and "
                 "switches to your caller's language automatically.",
    "start": "Just book a quick demo. We set up your free trial, connect your number, and Norra "
             "starts answering your calls — usually within a day or two.",
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
                    "Keep it natural and conversational, keep the names 'Nora' and 'Norra' in "
                    "English letters, and keep common English business words (appointment, lead, "
                    "business, free trial) as-is if that's how locals speak. Return ONLY the translation."},
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


def synth(text, label, engine, code, key):
    ext = "wav" if engine == "sarvam" else "mp3"
    fname = f"{key}_{label}.{ext}"
    path = os.path.join(OUT_DIR, fname)
    print(f"  {label} · {key} ({engine}) -> {fname}")
    if engine == "sarvam":
        sarvam_tts(text, code, path)
    else:
        openai_tts(text, path)
    return fname


def main():
    if not SARVAM_KEY or not OPENAI_KEY:
        raise SystemExit("Set SARVAM_API_KEY and OPENAI_API_KEY in india/.env")

    manifest = {}
    for label, (engine, code) in LANGS.items():
        manifest[label] = {}
        # intro
        if label == "English":
            intro_text = MASTER
        elif label == "Telugu":
            intro_text = TELUGU
        else:
            print(f"translating intro -> {label}")
            intro_text = translate(MASTER, label)
        manifest[label]["intro"] = synth(intro_text, label, engine, code, "intro")
        # FAQ answers
        for key, ans in FAQ.items():
            text = ans if label == "English" else translate(ans, label)
            manifest[label][key] = synth(text, label, engine, code, key)

    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in manifest.values())
    print(f"\n✅ Done. {total} clips in {OUT_DIR}")
    print("   Listen, then host them with: cd ../aws && terraform apply")


if __name__ == "__main__":
    main()
