"""
Norra — Indian AI receptionist (Pipecat Cloud + Gemini Live).

ONE configurable agent that becomes a top-class receptionist for ANY business and vertical
(clinic, real estate, restaurant, salon, home services, ...). Telugu-first, multilingual,
with a warm, human Gemini Live voice and a selectable voice per business.

Three layers build every prompt:
  CORE      — the shared "excellent, human receptionist" spec (consistency + warmth).
  PLAYBOOK  — the call goal + flow for that vertical (the value).
  PROFILE   — the specific business's info (name, hours, offerings, prices...).

The session body selects the profile/vertical, language and voice — so the same deployment
serves the website sales agent AND any clinic/real-estate/restaurant demo.
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
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments

load_dotenv(override=True)


# ---------------------------------------------------------------------------
# 1. CORE — shared spec that makes every Nora warm, human and consistent
# ---------------------------------------------------------------------------
CORE = """You are Nora, the warm, professional virtual receptionist for {business_name}. You answer the phone like an outstanding human front-desk person — friendly, calm and genuinely helpful. You are an AI assistant and say so honestly if asked, but you never sound robotic.

HOW YOU SOUND (most important):
- Warm, relaxed and human. Short, friendly sentences. Smile in your voice.
- Speak {language} as your main language, naturally mixing in the everyday English words locals use (appointment, booking, doctor, property, table, price...).
- Let the caller finish — never talk over them. If you miss something, gently ask them to repeat.
- Use the caller's first name once you know it. React like a person: "sure!", "of course", "no problem at all".
- Relaxed, natural pace — never rushed or scripted.

ALWAYS:
- Greet warmly and find out how you can help.
- When taking a phone number, repeat it back to confirm it's right.
- Read back any booking or details before confirming them.
- Use ONLY the facts in BUSINESS INFO below. If you don't know, say so honestly and offer to take a message for the team to call back. Never invent names, prices, times or availability.
- Keep the caller's information private.

NEVER:
- Never give medical, legal or financial advice — say a specialist will help during the visit or meeting.
- Never pretend to transfer a call you can't — take a detailed message instead.
- In any emergency, calmly tell the caller to hang up and call the local emergency number right away.

YOUR NAME: always say your name as the plain word "Nora"."""


# ---------------------------------------------------------------------------
# 2. PLAYBOOKS — the call goal + flow per vertical
# ---------------------------------------------------------------------------
PLAYBOOKS = {
    "clinic": (
        "THIS BUSINESS is a healthcare clinic. MAIN GOAL: book appointments.\n"
        "FLOW: understand the concern (never diagnose) -> which doctor or service if relevant -> "
        "preferred day and time within working hours -> collect full name and mobile number (confirm "
        "the number) -> read the appointment back -> confirm and say a WhatsApp confirmation is coming. "
        "Also answer timings, doctors, services, fees and location. A medical emergency -> tell them to "
        "hang up and call 108."
    ),
    "real_estate": (
        "THIS BUSINESS is a real estate office. MAIN GOAL: qualify the lead and book a site visit.\n"
        "FLOW: buying or renting? -> budget, preferred area, size/BHK, timeline -> share matching options "
        "from the listings below (only what's listed) -> offer a site visit with an agent (day/time) -> "
        "collect full name and mobile (confirm the number) -> read back and confirm -> say the team will "
        "follow up on WhatsApp. Capture every lead, even browsers."
    ),
    "restaurant": (
        "THIS BUSINESS is a restaurant. MAIN GOAL: take reservations and answer menu/timing questions.\n"
        "FLOW: reservation (party size, date, time, name, mobile — confirm the number) or takeaway "
        "interest -> read back and confirm -> answer about cuisine, timings, location and popular dishes "
        "from the info below -> note any special requests."
    ),
    "salon": (
        "THIS BUSINESS is a salon or spa. MAIN GOAL: book service appointments.\n"
        "FLOW: which service (and preferred stylist if any) -> preferred day and time within hours -> "
        "full name and mobile (confirm the number) -> read back and confirm -> WhatsApp confirmation. "
        "Answer about services, prices and timings."
    ),
    "home_services": (
        "THIS BUSINESS provides home or auto services. MAIN GOAL: capture the job and schedule a visit.\n"
        "FLOW: what's the problem or service needed -> area/location -> how urgent -> preferred time -> "
        "full name and mobile (confirm the number) -> explain the next step (no firm quote unless listed) "
        "-> confirm and capture the lead."
    ),
    "general": (
        "MAIN GOAL: understand the caller's need, answer from the info below, and capture their details "
        "(full name and mobile — confirm the number) so the team follows up. Take a clear message for "
        "anything you can't handle."
    ),
    "sales": (
        "YOU are Nora, an AI receptionist, talking to a business owner exploring whether to use you for "
        "their business. Speak about yourself and what you do in the FIRST PERSON (I answer calls, I book "
        "appointments). Do NOT say the brand name out loud — it sounds almost identical to your own name "
        "and confuses people; just be 'Nora, an AI receptionist'.\n"
        "OPENING: your very first reply must clearly introduce yourself — 'I'm Nora, an AI receptionist' — "
        "and say in one short line what you do: answer their business calls 24/7, book appointments and "
        "capture every lead. Then invite their questions.\n"
        "GOAL: explain what you can do, answer questions from the info below, and — if interested — book a "
        "quick demo or start their free 30-day trial (collect name and mobile, confirm the number). Lead "
        "with the free trial. Be confident, never pushy."
    ),
}


# ---------------------------------------------------------------------------
# 3. PROFILES — a business profile fully describes a business
#    Shape: {name, vertical, info, voice}
# ---------------------------------------------------------------------------
NORRA_SALES = {
    "name": "Norra",
    "vertical": "sales",
    "voice": "Aoede",
    "info": (
        "You are an AI receptionist for local businesses. You answer the phone 24/7, book appointments, "
        "capture every lead, and speak the caller's language (Telugu, Hindi, English, Tamil, Kannada, "
        "Malayalam...). Setup is done-for-you, usually a day or two. A business can forward its existing "
        "number to you or get a new one.\n"
        "FREE TRIAL: free for 30 days, up to 200 minutes, full setup included, cancel anytime.\n"
        "PRICING (India): Starter Rs 2,500/mo (300 min); Pro Rs 6,000/mo (1,000 min, most popular); Multi "
        "Rs 12,000/mo (2,500 min). Extra minutes ~Rs 5-6. Most businesses never exceed their plan.\n"
        "You are honest about being an AI; you hand off to a person when asked; data respects India's DPDP Act."
    ),
}

SAMPLE_CLINIC = {
    "name": "Sunshine Clinic",
    "vertical": "clinic",
    "voice": "Aoede",
    "info": (
        "Timings: Monday-Saturday 10 AM-8 PM, closed Sunday.\n"
        "Doctors: Dr. Rao (General Physician, mornings), Dr. Sharma (Pediatrician, evenings Mon-Fri).\n"
        "Services: general consultation, child health, vaccinations, basic lab tests. Fee: Rs 500.\n"
        "Address: Road No. 5, Banjara Hills, Hyderabad, near the metro. Parking available."
    ),
}

SAMPLE_REALESTATE = {
    "name": "Skyline Properties",
    "vertical": "real_estate",
    "voice": "Aoede",
    "info": (
        "We deal in apartments and plots in Hyderabad (Gachibowli, Kondapur, Banjara Hills).\n"
        "Listings: 2BHK in Kondapur ~Rs 85 lakh; 3BHK in Gachibowli ~Rs 1.4 crore; rental 2BHK in Madhapur "
        "~Rs 28,000/month.\n"
        "Site visits: Mon-Sat 10 AM-6 PM with an agent. Office: Gachibowli main road."
    ),
}

DEMOS = {"clinic": SAMPLE_CLINIC, "real_estate": SAMPLE_REALESTATE, "sales": NORRA_SALES}


# ---------------------------------------------------------------------------
# 4. Language / voice / prompt builder
# ---------------------------------------------------------------------------
GEMINI_LANGS = {
    "Telugu": "te-IN", "English": "en-US", "Hindi": "hi-IN",
    "Tamil": "ta-IN", "Kannada": "kn-IN", "Malayalam": "ml-IN",
}
# Gemini native-audio voices (accent/persona). Female: Aoede, Kore, Leda, Zephyr. Male: Puck, Charon.
DEFAULT_VOICE = os.getenv("GEMINI_VOICE", "Aoede")


def build_system_prompt(profile, lang_name):
    core = CORE.format(business_name=profile.get("name", "this business"), language=lang_name)
    playbook = PLAYBOOKS.get(profile.get("vertical", "general"), PLAYBOOKS["general"])

    # Live instructions the owner left (e.g. "doctor out 2 days", "put Mr. Rao through to me").
    # These take priority over the base info.
    notes = (profile.get("notes") or "").strip()
    notes_block = ""
    if notes:
        notes_block = (
            "\n\n=== TODAY'S INSTRUCTIONS FROM THE OWNER (these OVERRIDE the base info) ===\n"
            + notes
            + "\nHonor these for this call — e.g. closures/availability, who to put through to the owner, "
            "or what to tell callers. If they conflict with the base info, follow these."
        )

    return (
        core
        + "\n\n=== YOUR JOB ===\n" + playbook
        + "\n\n=== BUSINESS INFO (use only these facts) ===\n"
        + f"Business: {profile.get('name', '')}\n" + profile.get("info", "")
        + notes_block
        + f"\n\nSESSION LANGUAGE: speak {lang_name} for the whole call — warm, natural and human."
    )


# ---------------------------------------------------------------------------
# 5. Pipeline
# ---------------------------------------------------------------------------
async def main(transport, profile, lang_name="Telugu"):
    system = build_system_prompt(profile, lang_name)
    voice = profile.get("voice", DEFAULT_VOICE)

    # One Gemini Live model = listening + thinking + the natural voice.
    # NOTE: the native-audio model rejects explicit codes like te-IN, so we DON'T set `language`;
    # the language is driven by the system instruction ("speak Telugu") and the caller's speech.
    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        settings=GeminiLiveLLMService.Settings(
            voice=voice,
            system_instruction=system,
            temperature=0.8,
        ),
        inference_on_context_initialization=False,
    )

    context = LLMContext()
    user_agg, assistant_agg = LLMContextAggregatorPair(context)
    pipeline = Pipeline([transport.input(), user_agg, llm, transport.output(), assistant_agg])
    task = PipelineTask(pipeline, params=PipelineParams(enable_metrics=True))

    @transport.event_handler("on_first_participant_joined")
    async def _joined(transport, participant):
        logger.info(f"Caller joined — greeting in {lang_name}")
        if profile.get("vertical") == "sales":
            greet = (
                f"(The caller just connected.) In {lang_name}, warmly introduce yourself as 'Nora, an AI "
                "receptionist', clearly say in one short line what you do — answer their business calls "
                "24/7, book appointments and capture every lead — and ask what they'd like to know. Do NOT "
                "say the brand name aloud (it sounds like your own name). Two short, friendly sentences."
            )
        else:
            greet = (
                f"(The caller just connected.) Greet them warmly in {lang_name} as Nora from "
                f"{profile.get('name', '')}, and ask how you can help. One or two short, natural sentences."
            )
        context.add_message({"role": "user", "content": greet})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_participant_left")
    async def _left(transport, participant, reason):
        logger.info("Caller left")
        await task.cancel()

    await PipelineRunner(handle_sigint=False, force_gc=True).run(task)


async def bot(args: DailySessionArguments):
    """Entry point. The session body selects the business, language and voice.

    Body options:
      language   "Telugu" (default), "English", "Hindi", "Tamil", "Kannada", "Malayalam"
      demo       "clinic" | "real_estate" | "sales"   -> a built-in sample profile
      OR a full profile:  name, vertical, info, voice  -> any real business
    No body -> Norra's sales agent (used by the website).
    """
    try:
        body = args.body or {}
    except Exception:
        body = {}

    lang_name = body.get("language", "Telugu")

    if body.get("vertical") and body.get("info"):
        profile = {
            "name": body.get("name", "this business"),
            "vertical": body["vertical"],
            "info": body["info"],
            "voice": body.get("voice", DEFAULT_VOICE),
        }
    elif body.get("demo") in DEMOS:
        profile = dict(DEMOS[body["demo"]])
    else:
        profile = dict(NORRA_SALES)

    # Live instructions left by the owner (demo console field today; WhatsApp voice notes later).
    if body.get("notes"):
        profile["notes"] = body["notes"]

    logger.info(f"Norra starting — {profile['vertical']} / {profile['name']} / {lang_name}")
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
    await main(transport, profile, lang_name)
