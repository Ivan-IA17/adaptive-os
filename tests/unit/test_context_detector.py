"""Unit tests for the Context Detector."""

import pytest
from adaptive_os.detectors.context import ContextSnapshot


class TestContextSnapshot:

    def test_to_llm_text_contains_key_fields(self):
        snap = ContextSnapshot(
            active_apps=["code", "alacritty", "firefox"],
            focused_window="adaptive-os — VSCode",
            cpu_percent=45.0,
            ram_percent=60.0,
            gpu_active=False,
            gamepad_connected=False,
            audio_output="headphones",
            hour=14,
            day_of_week=1,  # Tuesday
            is_weekend=False,
            recent_profiles=["work", "work"],
        )
        text = snap.to_llm_text()
        assert "code" in text
        assert "14:00" in text
        assert "Tuesday" in text
        assert "headphones" in text
        assert "work" in text

    def test_to_dict_is_serialisable(self):
        import json
        snap = ContextSnapshot(active_apps=["vim"], hour=9)
        d = snap.to_dict()
        # Should be JSON-serialisable
        json.dumps(d)

    def test_weekend_detection(self):
        snap = ContextSnapshot(day_of_week=6, is_weekend=True)
        text = snap.to_llm_text()
        assert "weekend" in text
