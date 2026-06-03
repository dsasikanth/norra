"""
Norra India — LOCAL test (talk in your browser, no phone number needed).

This uses Pipecat's built-in WebRTC runner, so you just open a web page and talk —
no microphone libraries to install.

Setup:
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.sample .env        # set SARVAM_API_KEY, SARVAM_VOICE_ID=ritu, OPENAI_API_KEY
    python local_test.py

Then open the URL it prints (http://localhost:7860/client), click Connect, allow the
mic, and say "నమస్కారం" (namaskaram) — Norra greets you in Telugu. Ctrl+C to stop.
"""

from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams

from bot import run_bot


async def bot(runner_args: RunnerArguments):
    transport = await create_transport(
        runner_args,
        {"webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True)},
    )
    await run_bot(transport)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
