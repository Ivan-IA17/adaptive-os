"""
Integration tests for the full orchestrator flow.
Uses a mock Ollama server so no real LLM is needed.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from adaptive_os.core.config import Config, OllamaConfig, DetectionConfig
from adaptive_os.core.orchestrator import Orchestrator
from adaptive_os.core.state import StateDB
from adaptive_os.detectors.context import ContextSnapshot


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.db_path = tmp_path / "state.db"
    cfg.repo_root = tmp_path
    cfg.ollama.min_confidence = 0.75
    cfg.detection.interval = 999  # Don't auto-fire
    cfg.detection.switch_cooldown = 0  # No cooldown in tests
    return cfg


@pytest_asyncio.fixture
async def state(tmp_config: Config) -> StateDB:
    db = StateDB(tmp_config.db_path)
    await db.init()
    return db


@pytest_asyncio.fixture
async def orchestrator(tmp_config: Config) -> Orchestrator:
    orch = Orchestrator(tmp_config)
    await orch._state.init()
    return orch


# ── Mock helpers ──────────────────────────────────────────────────────────────

def mock_ollama_response(profile: str, confidence: float, reason: str = "test") -> dict:
    return {
        "message": {
            "content": json.dumps({
                "profile": profile,
                "confidence": confidence,
                "reason": reason,
            })
        }
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestManualSwitch:

    @pytest.mark.asyncio
    async def test_manual_switch_changes_profile(self, orchestrator: Orchestrator):
        with patch.object(orchestrator._manager, "_apply_ui", new_callable=AsyncMock), \
             patch.object(orchestrator._manager, "_switch_systemd_target", new_callable=AsyncMock), \
             patch.object(orchestrator._manager, "_apply_theme", new_callable=AsyncMock), \
             patch.object(orchestrator._manager, "_notify", new_callable=AsyncMock):

            result = await orchestrator.manual_switch("gaming")

        assert result["success"] is True
        assert result["profile"] == "gaming"
        assert orchestrator._manager.current_profile == "gaming"

    @pytest.mark.asyncio
    async def test_manual_switch_records_history(self, orchestrator: Orchestrator, state: StateDB):
        orchestrator._state = state
        orchestrator._manager._state = state

        with patch.object(orchestrator._manager, "_apply_ui", new_callable=AsyncMock), \
             patch.object(orchestrator._manager, "_switch_systemd_target", new_callable=AsyncMock), \
             patch.object(orchestrator._manager, "_apply_theme", new_callable=AsyncMock), \
             patch.object(orchestrator._manager, "_notify", new_callable=AsyncMock):

            await orchestrator.manual_switch("creative", reason="testing")

        recent = await state.recent_profiles(n=1)
        assert recent == ["creative"]

    @pytest.mark.asyncio
    async def test_switch_to_same_profile_is_noop(self, orchestrator: Orchestrator):
        orchestrator._manager._current = "work"

        with patch.object(orchestrator._manager, "_apply_ui", new_callable=AsyncMock) as mock_ui:
            result = await orchestrator.manual_switch("work")

        mock_ui.assert_not_called()
        assert result["profile"] == "work"


class TestContextDetectionLoop:

    @pytest.mark.asyncio
    async def test_high_confidence_triggers_switch(self, orchestrator: Orchestrator):
        gaming_snapshot = ContextSnapshot(
            active_apps=["steam", "gamemode"],
            gamepad_connected=True,
            hour=20,
        )

        with patch.object(orchestrator._detector, "sample",
                          new_callable=AsyncMock,
                          return_value=gaming_snapshot), \
             patch.object(orchestrator._engine, "decide",
                          new_callable=AsyncMock,
                          return_value=MagicMock(
                              profile="gaming", confidence=0.95,
                              reason="Steam+gamepad", is_actionable=True
                          )), \
             patch.object(orchestrator._manager, "switch",
                          new_callable=AsyncMock,
                          return_value=True) as mock_switch, \
             patch.object(orchestrator._state, "record_snapshot",
                          new_callable=AsyncMock), \
             patch.object(orchestrator._state, "recent_profiles",
                          new_callable=AsyncMock, return_value=[]):

            await orchestrator._tick()

        mock_switch.assert_called_once_with(
            "gaming",
            reason="Steam+gamepad",
            confidence=0.95,
            triggered_by="auto",
        )

    @pytest.mark.asyncio
    async def test_low_confidence_skips_switch(self, orchestrator: Orchestrator):
        with patch.object(orchestrator._detector, "sample",
                          new_callable=AsyncMock,
                          return_value=ContextSnapshot()), \
             patch.object(orchestrator._engine, "decide",
                          new_callable=AsyncMock,
                          return_value=MagicMock(
                              profile="gaming", confidence=0.4,
                              is_actionable=False
                          )), \
             patch.object(orchestrator._manager, "switch",
                          new_callable=AsyncMock) as mock_switch, \
             patch.object(orchestrator._state, "record_snapshot",
                          new_callable=AsyncMock), \
             patch.object(orchestrator._state, "recent_profiles",
                          new_callable=AsyncMock, return_value=[]):

            await orchestrator._tick()

        mock_switch.assert_not_called()


class TestConversationalInterface:

    @pytest.mark.asyncio
    async def test_ask_with_profile_keyword_triggers_switch(self, orchestrator: Orchestrator):
        with patch.object(orchestrator._engine, "ask",
                          new_callable=AsyncMock,
                          return_value="I'll switch to gaming mode for you."), \
             patch.object(orchestrator, "manual_switch",
                          new_callable=AsyncMock,
                          return_value={"success": True, "profile": "gaming"}) as mock_switch:

            result = await orchestrator.ask("I want to play some games")

        mock_switch.assert_called_once_with("gaming", reason=pytest.approx(str, abs=0))
        assert "answer" in result

    @pytest.mark.asyncio
    async def test_status_returns_expected_keys(self, orchestrator: Orchestrator):
        with patch.object(orchestrator._state, "recent_profiles",
                          new_callable=AsyncMock, return_value=["work"]):
            status = await orchestrator.status()

        assert "current_profile" in status
        assert "running" in status
        assert "ollama_model" in status
        assert "recent_profiles" in status


class TestStateDB:

    @pytest.mark.asyncio
    async def test_kv_roundtrip(self, state: StateDB):
        await state.set("test_key", {"foo": "bar", "num": 42})
        val = await state.get("test_key")
        assert val == {"foo": "bar", "num": 42}

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_default(self, state: StateDB):
        val = await state.get("nonexistent", default="fallback")
        assert val == "fallback"

    @pytest.mark.asyncio
    async def test_recent_profiles_ordering(self, state: StateDB):
        await state.record_switch("work")
        await state.record_switch("gaming")
        await state.record_switch("creative")

        recent = await state.recent_profiles(n=2)
        assert recent == ["creative", "gaming"]
