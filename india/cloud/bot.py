"""
Norra India — Telugu agent for Pipecat Cloud (Daily WebRTC).

Self-contained on purpose: Pipecat Cloud's Docker build only copies this one file.
Uses Sarvam (Telugu STT + TTS) + OpenAI LLM, same as the local agent.

Deploy: see README.md in this folder.
"""

import os

from dotenv import load_dotenv
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
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transcriptions.language import Language
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments

load_dotenv(override=True)

CLINIC_NAME = os.getenv("CLINIC_NAME", "Sunshine Clinic")
CLINIC_KNOWLEDGE = os.getenv(
    "CLINIC_KNOWLEDGE",
    "Timings: Monday to Saturday, 10 AM to 8 PM. Closed Sunday. "
    "Doctors: Dr. Rao (General Physician), Dr. Sharma (Pediatrics). "
    "Consultation fee: 500 rupees. Address: Road No. 5, Banjara Hills, Hyderabad.",
)

SYSTEM_PROMPT = f"""You are Norra, the friendly virtual receptionist for {CLINIC_NAME}, a clinic in Hyderabad.

LANGUAGE: Speak Telugu by default, mixing in the common English words people in Hyderabad
naturally use (appointment, doctor, report, timing, booking). Short, warm, natural sentences —
never robotic. If the caller switches to Hindi or English, follow them.

IDENTITY: Greet the caller, say you are the clinic's virtual assistant, and that the call may be
recorded. If asked whether you are a real person, say honestly that you are a virtual assistant
and offer to connect a staff member.

JOB: Answer questions about timings, doctors, services and fees using ONLY the knowledge base
below. To book, collect the caller's NAME and MOBILE NUMBER and the day/time, then read it back
to confirm.

GUARDRAILS: Only state facts from the knowledge base. No medical advice. For emergencies, tell
the caller to hang up and call 108.

KNOWLEDGE BASE:
{CLINIC_KNOWLEDGE}
"""

GREETING = (
    f"Greet the caller now in Telugu: warmly welcome them to {CLINIC_NAME}, "
    "introduce yourself as the virtual assistant Norra, and ask how you can help."
)


def build_services():
    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        mode="codemix",
        settings=SarvamSTTService.Settings(model="saaras:v3", language=Language.TE_IN),
    )
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )
    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        settings=SarvamTTSService.Settings(
            voice=os.getenv("SARVAM_VOICE_ID", "ritu"),
            model=os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"),
            language=Language.TE_IN,
        ),
    )
    return stt, llm, tts


async def main(transport):
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

    @transport.event_handler("on_first_participant_joined")
    async def _joined(transport, participant):
        logger.info("Participant joined — greeting in Telugu")
        context.add_message({"role": "system", "content": GREETING})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_participant_left")
    async def _left(transport, participant, reason):
        logger.info("Participant left")
        await task.cancel()

    await PipelineRunner(handle_sigint=False, force_gc=True).run(task)


async def bot(args: DailySessionArguments):
    """Pipecat Cloud entry point."""
    logger.info(f"Norra Telugu bot starting: room={args.room_url}")
    transport = DailyTransport(
        args.room_url,
        args.token,
        "Norra",
        DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )
    await main(transport)
