"""
Decision Engine — sends context snapshots to the local LLM (Ollama)
and returns a profile decision with confidence score and reasoning.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx

from adaptive_os.core.config import OllamaConfig
from adaptive_os.detectors.context import ContextSnapshot

logger = logging.getLogger(__name__)

KNOWN_PROFILES = ["work", "gaming", "creative", "server", "study"]

SYSTEM_PROMPT = """You are the decision engine for an AI-adaptive operating system.
Your task is to analyse the user's current system context and determine which
operating profile best matches their current activity.

Available profiles:
- work: software development, coding, DevOps, research browsing
- gaming: playing video games, gamepad connected, Steam/Lutris active
- creative: design, video editing, audio production, 3D modelling
- server: system administration, server management, night maintenance
- study: reading papers, taking notes, flashcards, academic work

You must respond with ONLY a valid JSON object — no explanation, no markdown:
{"profile": "<name>", "confidence": <0.0-1.0>, "reason": "<one sentence>"}

Confidence guide:
- 0.9+ : very obvious (e.g. Steam is open and gamepad connected)
- 0.75-0.9 : clear signals (e.g. VSCode + terminals + GitHub in browser)
- 0.5-0.75 : probable but ambiguous
- below 0.5 : not enough signal, keep current profile
"""


@dataclass
class ProfileDecision:
    profile: str
    confidence: float
    reason: str
    raw_response: str = ""

    @property
    def is_actionable(self) -> bool:
        """True if confidence is high enough to trigger an automatic switch."""
        return self.confidence >= 0.75 and self.profile in KNOWN_PROFILES


class DecisionEngine:
    """Queries Ollama with a context snapshot and returns a ProfileDecision."""

    def __init__(self, config: OllamaConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(timeout=config.timeout)

    async def decide(self, snapshot: ContextSnapshot) -> ProfileDecision:
        """Ask the LLM which profile best matches the current context."""
        user_message = (
            "Analyse this system context and decide the best profile:\n\n"
            + snapshot.to_llm_text()
        )

        try:
            response = await self._client.post(
                f"{self._config.host}/api/chat",
                json={
                    "model": self._config.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1},  # Low temperature for consistency
                },
            )
            response.raise_for_status()
            raw = response.json()["message"]["content"].strip()
            return self._parse_response(raw)

        except httpx.ConnectError:
            logger.error("Cannot reach Ollama at %s — is it running?", self._config.host)
            return ProfileDecision(profile="work", confidence=0.0,
                                   reason="Ollama unreachable, keeping current profile")
        except Exception as exc:
            logger.exception("Decision engine error: %s", exc)
            return ProfileDecision(profile="work", confidence=0.0,
                                   reason=f"Error: {exc}")

    def _parse_response(self, raw: str) -> ProfileDecision:
        """Parse the LLM JSON response into a ProfileDecision."""
        # Strip markdown fences if the model included them
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(clean)
            profile = str(data.get("profile", "work")).lower()
            confidence = float(data.get("confidence", 0.0))
            reason = str(data.get("reason", ""))

            if profile not in KNOWN_PROFILES:
                logger.warning("LLM returned unknown profile '%s', defaulting to work", profile)
                profile = "work"
                confidence = 0.0

            return ProfileDecision(profile=profile, confidence=confidence,
                                   reason=reason, raw_response=raw)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to parse LLM response: %s\nRaw: %s", exc, raw)
            return ProfileDecision(profile="work", confidence=0.0,
                                   reason="Parse error", raw_response=raw)

    async def ask(self, question: str) -> str:
        """Free-form question to the LLM about OS management (conversational interface)."""
        try:
            response = await self._client.post(
                f"{self._config.host}/api/chat",
                json={
                    "model": self._config.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an intelligent OS assistant. The user is talking to "
                                "their operating system. Help them switch profiles or configure "
                                "their system. Be concise and action-oriented. "
                                f"Available profiles: {', '.join(KNOWN_PROFILES)}."
                            ),
                        },
                        {"role": "user", "content": question},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except Exception as exc:
            return f"Error: {exc}"

    async def close(self) -> None:
        await self._client.aclose()
