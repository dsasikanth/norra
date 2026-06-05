"""
Norra India — Exotel dial-in server (Pipecat + Sarvam).

When a patient calls your Exotel number, Exotel's Voicebot applet opens a WebSocket
to /ws and streams the call audio here. This runs the same Telugu Norra pipeline
(Sarvam STT/TTS + LLM) and streams audio back.

Exotel specifics:
  - 8 kHz mono PCM audio (set in PipelineParams).
  - Pipecat auto-parses caller info (to/from) from Exotel's WebSocket messages.

Setup (you need these in india/.env):
  EXOTEL_API_KEY, EXOTEL_API_TOKEN, EXOTEL_ACCOUNT_SID, SARVAM_API_KEY, OPENAI_API_KEY

Run:
  python exotel_bot.py            # serves :8000
  ngrok http 8000                # expose it; put wss://<ngrok>/ws in the Voicebot applet
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.exotel import ExotelFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from bot import build_services, SYSTEM_PROMPT, GREETING_INSTRUCTION

load_dotenv()
app = FastAPI()


async def run_bot(transport):
    stt, llm, tts = build_services()

    context = LLMContext()
    context.add_message({"role": "system", "content": SYSTEM_PROMPT})
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_agg,
        llm,
        tts,
        transport.output(),
        assistant_agg,
    ])

    # Exotel streams 8 kHz mono PCM — match it.
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def _connected(transport, client):
        logger.info("Caller connected — greeting in Telugu")
        context.add_message({"role": "system", "content": GREETING_INSTRUCTION})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _disconnected(transport, client):
        logger.info("Caller disconnected")
        await task.cancel()

    await PipelineRunner(handle_sigint=False).run(task)


@app.websocket("/ws")
async def media_stream(websocket: WebSocket):
    await websocket.accept()

    # Pipecat parses Exotel's first messages: stream_id, call_id, account_sid, from, to
    _transport_type, call_data = await parse_telephony_websocket(websocket)
    logger.info(f"Incoming Exotel call from {call_data.get('from')} to {call_data.get('to')}")

    serializer = ExotelFrameSerializer(
        stream_id=call_data["stream_id"],
        call_id=call_data["call_id"],
        account_sid=call_data["account_sid"],
        api_key=os.getenv("EXOTEL_API_KEY"),
        api_token=os.getenv("EXOTEL_API_TOKEN"),
    )

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
    return {"ok": True, "service": "norra-exotel"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("exotel_bot:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
