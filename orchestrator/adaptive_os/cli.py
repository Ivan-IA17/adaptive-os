"""
adaptive-os CLI — control your adaptive system from the terminal.

Usage:
  adaptive-os start              Start the orchestrator daemon
  adaptive-os stop               Stop the daemon
  adaptive-os status             Show current profile and system state
  adaptive-os switch <profile>   Manually switch to a profile
  adaptive-os ask "<question>"   Tell the OS what you want to do
  adaptive-os logs               Follow orchestrator logs
  adaptive-os config get <key>   Get a config value
  adaptive-os config set <k> <v> Set a config value
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.panel import Panel

API_URL = "http://127.0.0.1:7979"
console = Console()

PROFILE_ICONS = {
    "work": "🖥️",
    "gaming": "🎮",
    "creative": "🎨",
    "server": "🖧",
    "study": "📖",
}


def api(method: str, path: str, **kwargs) -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            response = getattr(client, method)(f"{API_URL}{path}", **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        console.print("[red]✗ Orchestrator is not running.[/red] Start it with: adaptive-os start")
        sys.exit(1)


@click.group()
def cli() -> None:
    """🧠 Adaptive OS — AI-driven system orchestrator."""


@cli.command()
@click.option("--verbose", "-v", is_flag=True)
def start(verbose: bool) -> None:
    """Start the AI orchestrator daemon."""
    console.print("[blue]Starting Adaptive OS orchestrator...[/blue]")
    cmd = [sys.executable, "-m", "adaptive_os.main"]
    if verbose:
        subprocess.run(cmd)
    else:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print("[green]✓ Orchestrator started.[/green]")


@cli.command()
def stop() -> None:
    """Stop the orchestrator daemon."""
    subprocess.run(["pkill", "-f", "adaptive_os.main"], capture_output=True)
    console.print("[yellow]Orchestrator stopped.[/yellow]")


@cli.command()
def status() -> None:
    """Show current profile and orchestrator status."""
    data = api("get", "/status")
    profile = data.get("current_profile", "unknown")
    icon = PROFILE_ICONS.get(profile, "❓")

    panel = Panel(
        f"[bold]{icon} {profile.upper()}[/bold]\n\n"
        f"Running: {'[green]yes[/green]' if data.get('running') else '[red]no[/red]'}\n"
        f"Model: [cyan]{data.get('ollama_model', 'unknown')}[/cyan]\n"
        f"Detection interval: {data.get('detection_interval', '?')}s\n"
        f"Recent profiles: {' → '.join(data.get('recent_profiles', []))}",
        title="[bold blue]Adaptive OS Status[/bold blue]",
        border_style="blue",
    )
    console.print(panel)


@cli.command()
@click.argument(
    "profile",
    type=click.Choice(["work", "gaming", "creative", "server", "study"], case_sensitive=False),
)
def switch(profile: str) -> None:
    """Manually switch to a profile."""
    with console.status(f"Switching to [bold]{profile}[/bold]..."):
        result = api("post", f"/switch/{profile}")
    if result.get("success"):
        icon = PROFILE_ICONS.get(profile, "")
        console.print(f"[green]✓ Switched to {icon} [bold]{profile}[/bold][/green]")
    else:
        console.print("[red]✗ Switch failed[/red]")


@cli.command()
@click.argument("question")
def ask(question: str) -> None:
    """Tell the OS what you want to do (natural language)."""
    with console.status("Thinking..."):
        result = api("post", "/ask", json={"question": question})

    console.print(
        Panel(
            result.get("answer", "No response"),
            title="[bold cyan]Adaptive OS[/bold cyan]",
            border_style="cyan",
        )
    )
    profile = result.get("current_profile")
    if profile:
        icon = PROFILE_ICONS.get(profile, "")
        console.print(f"Active profile: {icon} [bold]{profile}[/bold]")


@cli.command()
def report() -> None:
    """Show weekly habit usage report."""
    result = api("get", "/report")
    console.print(
        Panel(
            result.get("report", "No data yet — use Adaptive OS for a few days first."),
            title="[bold blue]Weekly Usage Report[/bold blue]",
            border_style="blue",
        )
    )


@cli.command()
@click.option("--model", default=None, help="Path to whisper.cpp model file")
def voice(model: str | None) -> None:
    """Start voice interface (requires whisper.cpp + a model)."""
    import asyncio
    from adaptive_os.core.config import Config
    from adaptive_os.core.orchestrator import Orchestrator
    from adaptive_os.core.voice_interface import VoiceInterface
    from pathlib import Path

    async def _run() -> None:
        cfg = Config.load()
        orch = Orchestrator(cfg)
        await orch._state.init()
        model_path = Path(model) if model else None
        vi = VoiceInterface(orch, model_path=model_path)
        if not vi.available:
            console.print(
                "[red]✗ whisper.cpp not found.[/red]\n"
                "Install it: [cyan]https://github.com/ggerganov/whisper.cpp[/cyan]\n"
                "Get a model: [cyan]adaptive-os voice --help[/cyan]"
            )
            return
        console.print("[green]🎙 Voice interface starting...[/green]")
        console.print(
            "Say [bold]'Hey Ada'[/bold] to activate, [bold]'stop listening'[/bold] to quit."
        )
        await vi.start()

    asyncio.run(_run())


@cli.command()
def logs() -> None:
    """Follow orchestrator logs."""
    log_path = Path("~/.local/share/adaptive-os/adaptive-os.log").expanduser()
    if not log_path.exists():
        console.print("[yellow]No log file found yet. Start the orchestrator first.[/yellow]")
        return
    subprocess.run(["tail", "-f", str(log_path)])


@cli.group()
def config() -> None:
    """Get or set configuration values."""


@config.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get a configuration value."""
    from adaptive_os.core.config import Config

    cfg = Config.load()
    parts = key.split(".")
    val = cfg.model_dump()
    for p in parts:
        val = val.get(p, {})
    console.print(f"[cyan]{key}[/cyan] = [yellow]{val}[/yellow]")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    from adaptive_os.core.config import Config

    cfg = Config.load()
    d = cfg.model_dump()
    parts = key.split(".")
    target = d
    for p in parts[:-1]:
        target = target.setdefault(p, {})
    # Try to coerce to int/float/bool
    for cast in (int, float):
        try:
            value = cast(value)  # type: ignore
            break
        except ValueError:
            pass
    if value == "true":
        value = True  # type: ignore
    elif value == "false":
        value = False  # type: ignore
    target[parts[-1]] = value
    new_cfg = Config(**d)
    new_cfg.save()
    console.print(f"[green]✓ Set[/green] [cyan]{key}[/cyan] = [yellow]{value}[/yellow]")
