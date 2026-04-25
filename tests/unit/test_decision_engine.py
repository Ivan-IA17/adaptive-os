"""Unit tests for the Decision Engine."""

import pytest
from adaptive_os.core.decision_engine import DecisionEngine, ProfileDecision
from adaptive_os.core.config import OllamaConfig


class TestDecisionParsing:
    """Test LLM response parsing without network calls."""

    def _engine(self) -> DecisionEngine:
        return DecisionEngine(OllamaConfig())

    def test_parse_valid_response(self):
        engine = self._engine()
        raw = '{"profile": "gaming", "confidence": 0.92, "reason": "Steam is open and gamepad connected"}'
        decision = engine._parse_response(raw)
        assert decision.profile == "gaming"
        assert decision.confidence == pytest.approx(0.92)
        assert "Steam" in decision.reason

    def test_parse_with_markdown_fences(self):
        engine = self._engine()
        raw = '```json\n{"profile": "work", "confidence": 0.85, "reason": "VSCode open"}\n```'
        decision = engine._parse_response(raw)
        assert decision.profile == "work"
        assert decision.confidence == pytest.approx(0.85)

    def test_parse_unknown_profile_defaults_to_work(self):
        engine = self._engine()
        raw = '{"profile": "unknownprofile", "confidence": 0.9, "reason": "test"}'
        decision = engine._parse_response(raw)
        assert decision.profile == "work"
        assert decision.confidence == 0.0  # Reset on unknown profile

    def test_parse_invalid_json_returns_safe_default(self):
        engine = self._engine()
        decision = engine._parse_response("not valid json at all")
        assert decision.profile == "work"
        assert decision.confidence == 0.0

    def test_is_actionable_high_confidence(self):
        d = ProfileDecision(profile="gaming", confidence=0.9, reason="test")
        assert d.is_actionable is True

    def test_is_actionable_low_confidence(self):
        d = ProfileDecision(profile="gaming", confidence=0.5, reason="test")
        assert d.is_actionable is False

    def test_is_actionable_unknown_profile(self):
        d = ProfileDecision(profile="unknown", confidence=0.95, reason="test")
        assert d.is_actionable is False
