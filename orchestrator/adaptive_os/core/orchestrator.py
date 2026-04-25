"""
Main Orchestrator — the central event loop that ties together:
- ContextDetector (what is the user doing?)
- DecisionEngine  (which profile fits?)
- ProfileManager  (apply the profile)
- REST API        (expose control endpoints)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from adaptive_os.core.config import Config
from adaptive_os.core.decision_engine import DecisionEngine
from adaptive_os.core.state import StateDB
from adaptive_os.detectors.context import ContextDetector, ContextSnapshot
from adaptive_os.profiles.manager import ProfileManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central controller.

    Detection loop:
      every `config.detection.interval` seconds →
        sample context → ask LLM → maybe switch profile
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._state = StateDB(config.db_path)
        self._detector = ContextDetector()
        self._engine = DecisionEngine(config.ollama)
        self._manager = ProfileManager(config, self._state)

        self._last_switch_time: float = 0.0
        self._running = False
        self._last_snapshot: ContextSnapshot | None = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialise state and start the detection loop."""
        await self._state.init()

        # Restore last known profile
        saved = await self._state.get("current_profile", self._config.initial_profile)
        self._manager._current = saved
        logger.info("Adaptive OS started. Current profile: %s", saved)

        self._running = True
        await self._detection_loop()

    async def stop(self) -> None:
        self._running = False
        await self._engine.close()
        logger.info("Adaptive OS stopped.")

    # ── Detection loop ───────────────────────────────────────────────────────

    async def _detection_loop(self) -> None:
        interval = self._config.detection.interval
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.exception("Detection loop error: %s", exc)
            await asyncio.sleep(interval)

    async def _tick(self) -> None:
        """One detection cycle: sample → decide → maybe switch."""
        recent = await self._state.recent_profiles(n=5)
        snapshot = await self._detector.sample(recent_profiles=recent)
        self._last_snapshot = snapshot

        await self._state.record_snapshot(snapshot.to_dict())

        decision = await self._engine.decide(snapshot)
        logger.debug("Decision: profile=%s confidence=%.2f reason=%s",
                     decision.profile, decision.confidence, decision.reason)

        if not decision.is_actionable:
            logger.debug("Confidence too low (%.2f), keeping current profile.", decision.confidence)
            return

        cooldown = self._config.detection.switch_cooldown
        since_last = time.monotonic() - self._last_switch_time
        if since_last < cooldown:
            logger.debug("In cooldown (%ds remaining), skipping switch.", int(cooldown - since_last))
            return

        if decision.profile != self._manager.current_profile:
            success = await self._manager.switch(
                decision.profile,
                reason=decision.reason,
                confidence=decision.confidence,
                triggered_by="auto",
            )
            if success:
                self._last_switch_time = time.monotonic()

    # ── Public API (called by REST endpoints and CLI) ────────────────────────

    async def manual_switch(self, profile: str, reason: str = "manual") -> dict[str, Any]:
        """Force a profile switch regardless of cooldown."""
        success = await self._manager.switch(
            profile, reason=reason, confidence=1.0, triggered_by="manual"
        )
        self._last_switch_time = time.monotonic()
        return {"success": success, "profile": profile}

    async def ask(self, question: str) -> dict[str, Any]:
        """
        Conversational interface: the user tells the OS what they want to do.
        The LLM interprets the intent and triggers the appropriate profile.
        """
        answer = await self._engine.ask(question)

        # Try to extract a profile name from the LLM answer and act on it
        for profile in ["work", "gaming", "creative", "server", "study"]:
            if profile in answer.lower():
                await self.manual_switch(profile, reason=f"User asked: {question[:60]}")
                break

        return {"answer": answer, "current_profile": self._manager.current_profile}

    async def status(self) -> dict[str, Any]:
        recent = await self._state.recent_profiles(n=5)
        return {
            "current_profile": self._manager.current_profile,
            "running": self._running,
            "ollama_model": self._config.ollama.model,
            "detection_interval": self._config.detection.interval,
            "recent_profiles": recent,
            "last_snapshot": self._last_snapshot.to_dict() if self._last_snapshot else None,
        }
