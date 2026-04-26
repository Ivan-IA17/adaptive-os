"""
Voice Interface — speech-to-text via whisper.cpp (local, no cloud).

Pipeline:
  Microphone → whisper.cpp → text → Orchestrator.ask() → profile switch + TTS response

Requirements:
  - whisper.cpp built with: cmake -DWHISPER_CUBLAS=1 .. && make
  - A whisper model: ggml-base.en.bin or ggml-small.bin
  - espeak-ng or piper-tts for text-to-speech response

Start with: adaptive-os voice
Stop with:  Ctrl+C or say "stop listening"
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

WHISPER_MODELS = [
    Path.home() / ".local" / "share" / "whisper" / "ggml-base.bin",
    Path.home() / ".local" / "share" / "whisper" / "ggml-small.bin",
    Path("/usr/share/whisper/ggml-base.bin"),
]

WAKE_WORDS = {"hey ada", "hey adaptive", "adaptive os", "hey os"}
STOP_WORDS = {"stop listening", "goodbye", "exit", "quit"}


class VoiceInterface:
    """
    Listens for voice commands and routes them to the orchestrator.

    Uses whisper.cpp for STT (runs entirely locally).
    Uses espeak-ng or piper for TTS responses.
    """

    def __init__(self, orchestrator, model_path: Path | None = None) -> None:
        self._orchestrator = orchestrator
        self._model = model_path or self._find_model()
        self._whisper_bin = shutil.which("whisper-cli") or shutil.which("main")
        self._running = False

    def _find_model(self) -> Path | None:
        for path in WHISPER_MODELS:
            if path.exists():
                return path
        return None

    @property
    def available(self) -> bool:
        """True if whisper.cpp binary and a model are both found."""
        return self._whisper_bin is not None and self._model is not None

    async def start(self) -> None:
        """Start the voice listening loop."""
        if not self.available:
            raise RuntimeError(
                "whisper.cpp not found. Install it from https://github.com/ggerganov/whisper.cpp\n"
                "Then download a model: wget -P ~/.local/share/whisper/ "
                "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
            )

        logger.info("Voice interface started. Say 'Hey Ada' to activate.")
        await self._speak("Adaptive OS voice interface ready. Say hey Ada to activate.")
        self._running = True

        try:
            while self._running:
                audio_file = await self._record_chunk(seconds=3)
                text = await self._transcribe(audio_file)
                if not text:
                    continue

                text_lower = text.lower().strip()
                logger.debug("Heard: %s", text)

                # Check for wake word
                if any(w in text_lower for w in WAKE_WORDS):
                    await self._speak("Yes?")
                    command_audio = await self._record_chunk(seconds=6)
                    command = await self._transcribe(command_audio)
                    if command:
                        await self._handle_command(command)

                # Check for stop word (no wake word required)
                elif any(w in text_lower for w in STOP_WORDS):
                    await self._speak("Goodbye.")
                    self._running = False

        except asyncio.CancelledError:
            self._running = False

    async def _record_chunk(self, seconds: int = 3) -> Path:
        """Record audio from the default microphone into a WAV temp file."""
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        # arecord: ALSA recorder — 16kHz mono (whisper.cpp requirement)
        proc = await asyncio.create_subprocess_exec(
            "arecord", "-q",
            "-f", "S16_LE", "-r", "16000", "-c", "1",
            "-d", str(seconds),
            str(tmp),
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return tmp

    async def _transcribe(self, audio_file: Path) -> str:
        """Run whisper.cpp on the audio file and return the transcript."""
        if not audio_file.exists() or audio_file.stat().st_size < 1000:
            return ""
        try:
            result = await asyncio.create_subprocess_exec(
                self._whisper_bin,
                "-m", str(self._model),
                "-f", str(audio_file),
                "--no-timestamps",
                "-l", "es",   # Spanish; change to "en" for English-only
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=15)
            text = stdout.decode().strip()
            # whisper.cpp outputs "[BLANK_AUDIO]" for silence
            if "[BLANK_AUDIO]" in text or not text:
                return ""
            return text
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("Transcription error: %s", exc)
            return ""
        finally:
            audio_file.unlink(missing_ok=True)

    async def _handle_command(self, command: str) -> None:
        """Route the voice command to the orchestrator."""
        logger.info("Voice command: %s", command)
        try:
            result = await self._orchestrator.ask(command)
            answer = result.get("answer", "Done.")
            # Truncate for TTS (don't read a paragraph aloud)
            tts_answer = answer.split(".")[0] + "."
            await self._speak(tts_answer)
        except Exception as exc:
            logger.error("Command handling error: %s", exc)
            await self._speak("Sorry, something went wrong.")

    async def _speak(self, text: str) -> None:
        """Speak text using espeak-ng or piper-tts."""
        tts = shutil.which("espeak-ng") or shutil.which("espeak") or shutil.which("piper")
        if not tts:
            logger.debug("No TTS engine found, skipping speech output.")
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                tts, text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10)
        except Exception as exc:
            logger.warning("TTS error: %s", exc)

    def stop(self) -> None:
        self._running = False
