"""Configuration management for the Adaptive OS orchestrator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    host: str = "http://localhost:11434"
    model: str = "llama3"
    timeout: int = 30
    # Minimum confidence score (0-1) to trigger an automatic profile switch
    min_confidence: float = 0.75


class DetectionConfig(BaseModel):
    # How often (seconds) the context detector samples the system
    interval: int = 30
    # Minimum seconds between automatic profile switches (cooldown)
    switch_cooldown: int = 120
    # How many recent context snapshots to include in the LLM prompt
    history_window: int = 3


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: Path = Path("~/.local/share/adaptive-os/adaptive-os.log").expanduser()
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 3


class Config(BaseModel):
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Absolute path to the adaptive-os repository root
    repo_root: Path = Field(
        default_factory=lambda: Path(
            os.environ.get("ADAPTIVE_OS_ROOT", Path.home() / "adaptive-os")
        )
    )
    # Path to the SQLite state database
    db_path: Path = Field(
        default_factory=lambda: Path("~/.local/share/adaptive-os/state.db").expanduser()
    )
    # Active profile override (set by environment or manual switch)
    initial_profile: str = os.environ.get("ADAPTIVE_OS_PROFILE", "work")

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load config from YAML file, falling back to defaults."""
        config_path = path or Path("~/.config/adaptive-os/config.yaml").expanduser()
        if config_path.exists():
            with open(config_path) as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()

    def save(self, path: Path | None = None) -> None:
        """Persist current config to YAML."""
        config_path = path or Path("~/.config/adaptive-os/config.yaml").expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(self.model_dump(mode="json"), f, default_flow_style=False)
