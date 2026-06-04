"""
Norra India — Telugu voice receptionist (Pipecat + Sarvam + Plivo)

This is the Norra-specific part of the agent: the providers (Sarvam STT/TTS,
LLM) and the Telugu clinic-receptionist persona. The Plivo telephony plumbing
lives in server.py.

Sarvam:
  - STT: saaras:v3 in "codemix" mode -> understands Telugu mixed with English
    (how Hyderabad actually speaks), language te-IN.
  - TTS: Bulbul, Telugu voice.
  - LLM: gpt-4o-mini by default (cheap, handles Telugu). To use Sarvam's own
    Indian LLM instead, see the commented block below.

Docs to confirm exact params for your installed pipecat version:
  STT  https://docs.pipecat.ai/server/services/stt/sarvam
  TTS  https://docs.pipecat.ai/server/services/tts/sarvam
"""

import os

from dotenv import load_dotenv
from loguru import logger

load_dotenv()  # read keys from .env for both server.py and local_test.py

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
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transcriptions.language import Language

# ---- Clinic config (replace per client, or load from your knowledge store) ----
CLINIC_NAME = os.getenv("CLINIC_NAME", "Sunshine Clinic")
CLINIC_KNOWLEDGE = os.getenv(
    "CLINIC_KNOWLEDGE",
    "Timings: Monday to Saturday, 10 AM to 8 PM. Closed Sunday. "
    "Doctors: Dr. Rao (General Physician), Dr. Sharma (Pediatrics). "
    "Consultation fee: 500 rupees. Address: Road No. 5, Banjara Hills, Hyderabad.",
)

SYSTEM_PROMPT = f"""You are Norra, the friendly virtual receptionist for {CLINIC_NAME}, a clinic in Hyderabad.

YOUR NAME: When you say your name in Telugu, always pronounce it softly as నోరా (No-raa) — never the hard నొర్రా.

LANGUAGE: Speak Telugu by default, mixing in the common English words people in Hyderabad
naturally use (for example: appointment, doctor, report, timing, booking). Keep sentences
short, warm and natural — never robotic. If the caller switches to Hindi or English, follow them.

IDENTITY & HONESTY: Greet the caller, say you are the clinic's virtual assistant, and that the
call may be recorded to help with their request. If asked whether you are a real person, say
honestly that you are a virtual assistant and offer to connect a staff member.

YOUR JOB: Find out why they are calling. Answer questions about timings, doctors, services and
fees using ONLY the knowledge base below. To book an appointment, collect the caller's NAME and
MOBILE NUMBER and the day/time they want. Read the appointment back to confirm before ending.

GUARDRAILS: Only state facts from the knowledge base. If you don't know something, say so and
offer to take a message. Do NOT give any medical advice or diagnosis. If the caller describes a
medical emergency, tell them to hang up and call 108 immediately.

TRANSFER: If the caller is upset, has a complex issue, or asks for a person, offer to take a
detailed message or connect them to clinic staff.

KNOWLEDGE BASE:
{CLINIC_KNOWLEDGE}
"""

GREETING_INSTRUCTION = (
    "Greet the caller now in Telugu: warmly welcome them to "
    f"{CLINIC_NAME}, introduce yourself as the virtual assistant Norra "
    "(say your name softly in Telugu as నోరా), and ask how you can help."
)


def build_services():
    """Create the Sarvam STT/TTS + LLM services."""
    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        mode="codemix",  # Telugu + English mixed speech
        settings=SarvamSTTService.Settings(
            model="saaras:v3",
            language=Language.TE_IN,
        ),
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )
    # ---- To use Sarvam's own Indian LLM instead of OpenAI (OpenAI-compatible) ----
    # llm = OpenAILLMService(
    #     api_key=os.getenv("SARVAM_API_KEY"),
    #     base_url="https://api.sarvam.ai/v1",
    #     model="sarvam-m",
    # )

    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        settings=SarvamTTSService.Settings(
            voice=os.getenv("SARVAM_VOICE_ID", "ritu"),  # ritu is a bulbul:v3 voice
            model=os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"),  # MUST match the voice's model line
            language=Language.TE_IN,
        ),
    )
    return stt, llm, tts


async def run_bot(transport):
    """Wire the pipeline for one call/session. `transport` is supplied by the caller
    (local WebRTC for the laptop test, or Plivo for the phone)."""
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

    task = PipelineTask(pipeline, params=PipelineParams(enable_metrics=True))

    @transport.event_handler("on_client_connected")
    async def _on_connected(transport, client):
        logger.info("Connected — greeting the caller in Telugu")
        context.add_message({"role": "system", "content": GREETING_INSTRUCTION})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _on_disconnected(transport, client):
        logger.info("Disconnected")
        await task.cancel()

    await PipelineRunner(handle_sigint=False).run(task)
