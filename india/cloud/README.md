# Norra Telugu — Pipecat Cloud deploy (web demo)

Hosts the **Sarvam Telugu Norra** on Pipecat Cloud so your friend gets a **shareable web link**
to demo it live in a browser — WebRTC, TURN and TLS all handled for you. One-human-one-bot
minutes are free; you only pay Sarvam + OpenAI usage.

> Production *phone* calls still go through self-hosted Plivo (`../server.py`). This is just the
> reliable web demo.

## Files
- `bot.py` — the Telugu agent (Sarvam STT/TTS + LLM), self-contained for the cloud build.
- `requirements.txt`, `Dockerfile` — built by Pipecat Cloud (base image `dailyco/pipecat-base`).
- `pcc-deploy.toml` — agent name + secrets + scaling.
- `.env.sample` — your keys, uploaded as a secret set (not committed).

## One-time setup
1. Create an account at **https://pipecat.daily.co** and **add a billing card** (required to deploy).
2. Install the CLI:
   ```bash
   uv tool install pipecat-ai-cli      # or: pipx install pipecat-ai-cli
   pipecat cloud auth login
   ```

## Deploy
```bash
cd india/cloud

# 1. keys -> a secret set named in pcc-deploy.toml
cp .env.sample .env          # fill in SARVAM_API_KEY, OPENAI_API_KEY (voice already = ritu)
pipecat cloud secrets set norra-telugu-secrets --file .env

# 2. build + deploy
pipecat cloud deploy
```

## Test it (the shareable demo)
- Open your **Pipecat Cloud dashboard** → the `norra-telugu` agent → **Sandbox** → **Connect**,
  allow the mic, and say "నమస్కారం". That sandbox URL is what your friend opens to demo.
- Or start a session via API:
  ```bash
  curl -X POST https://api.pipecat.daily.co/v1/public/norra-telugu/start \
    -H "Authorization: Bearer <your-public-api-key>" \
    -H "Content-Type: application/json"
  ```

## Per-clinic
Set `CLINIC_NAME` / `CLINIC_KNOWLEDGE` in `.env` and re-run the `secrets set` + `deploy` steps,
or pass them per session in the start request body.

## If a build/deploy error appears
This is bleeding-edge (the Sarvam plugin is new). The most likely snags:
- **Context/import errors** → the base image's Pipecat version differs from this code's. Tell me
  the exact error; usually a one-line fix or a version pin in `requirements.txt`.
- **Speaker/model mismatch** → `ritu` needs `bulbul:v3` (already set).
Paste the deploy log and I'll pin it.
