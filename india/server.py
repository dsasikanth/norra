"""
Norra India — Plivo telephony server (Pipecat)

Answers an inbound Plivo call and streams the audio into the Norra Telugu bot.

Flow:
  1. Plivo receives a call on your Indian number.
  2. Plivo hits POST /  (the "Answer URL" you set on the number) and we return
     XML telling Plivo to open a bidirectional audio WebSocket to /ws.
  3. Plivo connects to /ws; we hand that socket to Pipecat + run_bot().

NOTE ON VERSIONS: Pipecat's telephony API occasionally changes. The canonical,
always-up-to-date reference is the official example:
  https://github.com/pipecat-ai/pipecat-examples  ->  plivo-chatbot/inbound
If an import below fails, clone that example, then drop our bot.py in and import
run_bot from it — the persona/providers in bot.py are what matter.
"""

import os

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from bot import run_bot

app = FastAPI()

# Public host where this server is reachable (no scheme), e.g. norra-india.example.com
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost:7860")


@app.post("/")
async def answer_call(request: Request):
    """Plivo Answer URL — return XML that opens a bidirectional media stream."""
    ws_url = f"wss://{PUBLIC_HOST}/ws"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Stream bidirectional="true" keepCallAlive="true" '
        f'contentType="audio/x-l16;rate=8000">{ws_url}</Stream>'
        "</Response>"
    )
    return HTMLResponse(content=xml, media_type="application/xml")


@app.websocket("/ws")
async def media_stream(websocket: WebSocket):
    await websocket.accept()

    # The first Plivo message carries call/stream identifiers used by the serializer.
    serializer = PlivoFrameSerializer(websocket)

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer,
        ),
    )

    await run_bot(transport)


@app.get("/health")
async def health():
    return {"ok": True, "service": "norra-india"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
