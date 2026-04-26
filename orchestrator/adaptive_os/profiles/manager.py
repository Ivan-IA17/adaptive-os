"""
Profile Manager — executes profile switches by:
1. Rebuilding/activating the NixOS profile
2. Reloading Hyprland compositor config
3. Restarting Waybar with the new config
4. Applying GTK/Qt themes
5. Managing systemd user services
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

from adaptive_os.core.config import Config
from adaptive_os.core.state import StateDB

logger = logging.getLogger(__name__)


class ProfileManager:
    """Applies a named profile to the live system."""

    def __init__(self, config: Config, state: StateDB) -> None:
        self._config = config
        self._state = state
        self._repo = config.repo_root
        self._current: str = config.initial_profile

    @property
    def current_profile(self) -> str:
        return self._current

    async def switch(
        self,
        profile: str,
        reason: str = "",
        confidence: float = 1.0,
        triggered_by: str = "auto",
    ) -> bool:
        """Switch to the given profile. Returns True on success."""
        if profile == self._current:
            logger.debug("Already on profile '%s', skipping switch.", profile)
            return True

        logger.info(
            "Switching profile: %s → %s (confidence=%.2f, reason=%s)",
            self._current,
            profile,
            confidence,
            reason,
        )

        steps = [
            ("Applying UI config", self._apply_ui(profile)),
            ("Switching systemd target", self._switch_systemd_target(profile)),
            ("Applying theme", self._apply_theme(profile)),
            ("Sending notification", self._notify(profile, reason)),
        ]

        # NixOS rebuild only runs when the system has Nix installed
        if self._nix_available():
            steps.insert(0, ("Building NixOS profile", self._nix_switch(profile)))

        success = True
        for step_name, coro in steps:
            try:
                await coro
            except Exception as exc:
                logger.error("Step '%s' failed: %s", step_name, exc)
                success = False  # Continue with remaining steps

        if success or True:  # Always update state even on partial success
            self._current = profile
            await self._state.record_switch(profile, reason, confidence, triggered_by)
            await self._state.set("current_profile", profile)

        return success

    def _nix_available(self) -> bool:
        return subprocess.run(["which", "nix"], capture_output=True).returncode == 0

    async def _nix_switch(self, profile: str) -> None:
        """Run nixos-rebuild switch with the profile flake."""
        flake_path = self._repo / "nix"
        result = await asyncio.create_subprocess_exec(
            "nixos-rebuild",
            "switch",
            "--flake",
            f"{flake_path}#{profile}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(result.communicate(), timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"nixos-rebuild failed: {stderr.decode()[:500]}")

    async def _apply_ui(self, profile: str) -> None:
        """Reload Hyprland config and restart Waybar."""
        hypr_config = self._repo / "ui" / "hyprland" / f"{profile}.conf"
        waybar_config = self._repo / "ui" / "waybar" / f"{profile}.jsonc"

        if hypr_config.exists():
            await self._run(["hyprctl", "reload"])
            # Hyprland picks up the new conf if we set the env and reload
            # In practice, the conf is symlinked from the profile
            await self._symlink_and_reload_hyprland(hypr_config)

        if waybar_config.exists():
            await self._restart_waybar(waybar_config)

    async def _symlink_and_reload_hyprland(self, config_path: Path) -> None:
        """Point ~/.config/hypr/hyprland.conf at the profile config and reload."""
        target = Path("~/.config/hypr/hyprland.conf").expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            target.unlink()
        target.symlink_to(config_path.resolve())
        await self._run(["hyprctl", "reload"])

    async def _restart_waybar(self, config_path: Path) -> None:
        """Kill current waybar and launch with new config."""
        await self._run(["pkill", "-x", "waybar"], check=False)
        await asyncio.sleep(0.3)
        asyncio.create_task(
            asyncio.create_subprocess_exec(
                "waybar",
                "-c",
                str(config_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        )

    async def _switch_systemd_target(self, profile: str) -> None:
        """Activate the systemd user target for this profile."""
        target = f"adaptive-os-{profile}.target"
        await self._run(
            ["systemctl", "--user", "start", target],
            check=False,  # Target may not exist yet
        )

    async def _apply_theme(self, profile: str) -> None:
        """Apply GTK theme via gsettings or a theme script."""
        theme_dir = self._repo / "ui" / "themes" / profile
        script = theme_dir / "apply.sh"
        if script.exists():
            await self._run(["bash", str(script)], check=False)

    async def _notify(self, profile: str, reason: str) -> None:
        """Send a desktop notification about the profile switch."""
        icons = {
            "work": "computer",
            "gaming": "applications-games",
            "creative": "applications-multimedia",
            "server": "network-server",
            "study": "accessories-text-editor",
        }
        icon = icons.get(profile, "system-run")
        body = reason if reason else f"Switched to {profile.title()} mode"
        await self._run(
            ["notify-send", "-i", icon, "-t", "3000", f"Adaptive OS: {profile.title()}", body],
            check=False,
        )

    @staticmethod
    async def _run(cmd: list[str], check: bool = True) -> None:
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(result.communicate(), timeout=30)
        if check and result.returncode != 0:
            raise RuntimeError(f"Command {cmd[0]} failed: {stderr.decode()[:200]}")
