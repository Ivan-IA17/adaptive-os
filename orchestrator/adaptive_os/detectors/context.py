"""
Context Detector — samples the system every N seconds and produces
a structured snapshot describing what the user is currently doing.
"""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil


@dataclass
class ContextSnapshot:
    """A point-in-time description of the user's activity context."""

    # Running processes (names only, deduplicated)
    active_apps: list[str] = field(default_factory=list)

    # Title of the currently focused window (requires xdotool or hyprctl)
    focused_window: str = ""

    # Top-level domain of the active browser tab (requires browser extension)
    browser_domain: str = ""

    # System resource usage
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    gpu_active: bool = False

    # Connected hardware
    gamepad_connected: bool = False
    external_display: bool = False
    audio_output: str = "unknown"  # "headphones" | "speakers" | "hdmi"

    # Time context
    hour: int = 0
    day_of_week: int = 0  # 0=Monday … 6=Sunday
    is_weekend: bool = False

    # Recent profile history (for LLM context)
    recent_profiles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_llm_text(self) -> str:
        """Render the snapshot as a human-readable description for the LLM prompt."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        apps = ", ".join(self.active_apps[:10]) if self.active_apps else "none"
        recent = ", ".join(self.recent_profiles[:3]) if self.recent_profiles else "none"

        return (
            f"Time: {self.hour:02d}:00 on {day_names[self.day_of_week]}"
            f"{'(weekend)' if self.is_weekend else '(weekday)'}.\n"
            f"Active applications: {apps}.\n"
            f"Focused window: {self.focused_window or 'unknown'}.\n"
            f"CPU: {self.cpu_percent:.0f}%, RAM: {self.ram_percent:.0f}%.\n"
            f"GPU active: {self.gpu_active}.\n"
            f"Gamepad connected: {self.gamepad_connected}.\n"
            f"Audio output: {self.audio_output}.\n"
            f"Recent profiles used: {recent}."
        )


class ContextDetector:
    """Samples system state and returns a ContextSnapshot."""

    # Apps that strongly indicate a specific context
    _DEV_APPS = {"code", "nvim", "vim", "emacs", "alacritty", "kitty", "wezterm",
                  "git", "docker", "kubectl", "python3", "node", "cargo", "go"}
    _GAMING_APPS = {"steam", "lutris", "heroic", "gamemode", "wine", "proton",
                     "csgo", "minecraft", "factorio"}
    _CREATIVE_APPS = {"krita", "inkscape", "gimp", "blender", "obs", "audacity",
                       "davinci", "kdenlive", "ardour", "carla"}
    _STUDY_APPS = {"zotero", "anki", "obsidian", "evince", "okular", "calibre",
                    "foxit", "texstudio", "libreoffice"}

    async def sample(self, recent_profiles: list[str] | None = None) -> ContextSnapshot:
        """Take a full system sample and return a ContextSnapshot."""
        snap = ContextSnapshot(recent_profiles=recent_profiles or [])

        now = datetime.now()
        snap.hour = now.hour
        snap.day_of_week = now.weekday()
        snap.is_weekend = snap.day_of_week >= 5

        # Gather all data concurrently
        results = await asyncio.gather(
            self._get_processes(),
            self._get_focused_window(),
            self._get_system_resources(),
            self._get_hardware(),
            return_exceptions=True,
        )

        if not isinstance(results[0], Exception):
            snap.active_apps = results[0]  # type: ignore[assignment]
        if not isinstance(results[1], Exception):
            snap.focused_window = results[1]  # type: ignore[assignment]
        if not isinstance(results[2], Exception):
            cpu, ram = results[2]  # type: ignore[misc]
            snap.cpu_percent = cpu
            snap.ram_percent = ram
        if not isinstance(results[3], Exception):
            gamepad, display, audio = results[3]  # type: ignore[misc]
            snap.gamepad_connected = gamepad
            snap.external_display = display
            snap.audio_output = audio

        return snap

    async def _get_processes(self) -> list[str]:
        """Return deduplicated list of running process names."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._collect_processes)

    def _collect_processes(self) -> list[str]:
        seen: set[str] = set()
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info["name"] or "").lower().split()[0]
                if name and len(name) > 1:
                    seen.add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(seen)

    async def _get_focused_window(self) -> str:
        """Get the title of the focused window via hyprctl."""
        try:
            result = await asyncio.create_subprocess_exec(
                "hyprctl", "activewindow", "-j",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=2)
            import json
            data = json.loads(stdout)
            return data.get("title", "")
        except Exception:
            return ""

    async def _get_system_resources(self) -> tuple[float, float]:
        loop = asyncio.get_event_loop()
        cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0.5))
        ram = psutil.virtual_memory().percent
        return cpu, ram

    async def _get_hardware(self) -> tuple[bool, bool, str]:
        """Detect gamepad, external displays, and audio output."""
        gamepad = await self._detect_gamepad()
        display = await self._detect_external_display()
        audio = await self._detect_audio_output()
        return gamepad, display, audio

    async def _detect_gamepad(self) -> bool:
        """Check /dev/input for gamepad devices."""
        try:
            input_dir = Path("/dev/input")
            return any(
                p.name.startswith("js") or p.name.startswith("event")
                for p in input_dir.iterdir()
                if p.is_char_device()
            )
        except Exception:
            return False

    async def _detect_external_display(self) -> bool:
        """Check for external displays via hyprctl."""
        try:
            result = await asyncio.create_subprocess_exec(
                "hyprctl", "monitors", "-j",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=2)
            import json
            monitors = json.loads(stdout)
            return len(monitors) > 1
        except Exception:
            return False

    async def _detect_audio_output(self) -> str:
        """Detect current audio output device type via pactl."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pactl", "get-default-sink",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=2)
            sink = stdout.decode().strip().lower()
            if "hdmi" in sink or "dp" in sink:
                return "hdmi"
            if "headphone" in sink or "headset" in sink:
                return "headphones"
            return "speakers"
        except Exception:
            return "unknown"
