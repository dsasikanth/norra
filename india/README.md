# Norra India — Telugu Voice Receptionist (self-hosted)

**Stack:** Pipecat (open-source orchestration) + Sarvam (Telugu STT/TTS) + OpenAI/Sarvam LLM + Plivo (Indian phone number).
**Economics:** ~₹3.5/min all-in. Healthy margin on the Pro/Multi plans (see `../Norra-India-Cost-Model.xlsx`).

This runs on **your own server** — no per-minute platform fee. You pay only Sarvam (usage), the LLM (usage), and Plivo (telephony + number).

---

## What you'll need (accounts)

| Service | Where | Notes |
|---|---|---|
| **Sarvam** | dashboard.sarvam.ai | API key. ₹1,000 free credits to start. |
| **OpenAI** | platform.openai.com | API key for the LLM (or skip and use Sarvam's LLM — see `bot.py`). |
| **Plivo** | console.plivo.com | Auth ID, Auth Token, and an Indian voice number. |
| **A server** | AWS EC2 / Hetzner / DigitalOcean | A small box (2 vCPU / 4 GB) is plenty to start: ~₹2,500/mo. |

> **India regulatory:** an Indian phone number needs **DLT registration (TRAI)** + KYC before it can take calls. Start this with Plivo **early** — it can take a few days. You can build and test everything else (even via a temporary/ngrok web path) while DLT is pending.

---

## Files here

| File | What it is |
|---|---|
| `bot.py` | The Norra agent — Sarvam Telugu STT/TTS + LLM + the receptionist persona. **This is the part you customize per client.** |
| `server.py` | Plivo answer webhook + audio WebSocket that feeds the bot. |
| `.env.sample` | Copy to `.env` and fill in your keys. |
| `requirements.txt`, `Dockerfile`, `docker-compose.yml` | To run it. |

---

## Quick test on your laptop (before you have a number)

```bash
cd india
cp .env.sample .env          # fill in SARVAM_API_KEY, OPENAI_API_KEY, PUBLIC_HOST
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py             # starts on :7860
```

In another terminal, expose it so Plivo can reach it:
```bash
ngrok http 7860
# copy the host it gives you (e.g. 1a2b3c.ngrok-free.app) into PUBLIC_HOST in .env, then restart server.py
```

> **Tip:** the most reliable scaffold for the Plivo transport is the official
> example repo `pipecat-ai/pipecat-examples` → `plivo-chatbot/inbound`. If a
> pipecat version bump breaks an import in `server.py`, clone that example and
> drop our `bot.py` into it — `bot.py` (providers + Telugu persona) is the part
> that's uniquely Norra.

---

## Production (self-hosted, Docker)

On your server:
```bash
git clone <your repo>  &&  cd india
cp .env.sample .env     # fill in ALL values; set PUBLIC_HOST to your domain (e.g. india.norrahq.com)
docker compose up -d --build
```

Put it behind a domain with TLS (Caddy or Nginx) so Plivo can reach `wss://india.norrahq.com/ws`.
Point an A record at the server and let Caddy auto-issue the certificate.

---

## Connect the Plivo number

1. In the Plivo console, buy/assign an **Indian voice number** (after DLT/KYC).
2. Create an **Application** with **Answer URL** = `https://<PUBLIC_HOST>/`  (method POST).
3. Assign that application to your number.
4. Call the number from a phone → Norra should answer in Telugu.

---

## Choosing the Telugu voice

In the Sarvam dashboard, audition the **Bulbul** Telugu voices, then set the one you like as
`SARVAM_VOICE_ID` in `.env`. The STT is set to `saaras:v3` **codemix** mode so it understands
Telugu mixed with English — the way Hyderabad actually speaks.

---

## Per-client setup

For each clinic, set `CLINIC_NAME` and `CLINIC_KNOWLEDGE` (timings, doctors, fees, address) in
`.env` — or wire `bot.py` to pull the knowledge from your own store. One server can run many
clients; route by the Plivo number that was dialed.

---

## Cost reminder

- ~₹3.5/min variable (Sarvam + LLM + Plivo inbound) once self-hosted.
- One small server (~₹2,500/mo) covers **all** your clients.
- Don't put high-volume clinics on the cheap Starter plan — see the cost model.

## Confirm before committing prices
All figures are planning estimates. Confirm live Sarvam / Plivo rates and your real call volumes
before you quote a clinic a fixed monthly price.
