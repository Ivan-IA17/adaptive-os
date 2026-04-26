# AI Orchestrator — Technical Reference

## Overview

The orchestrator is the brain of Adaptive OS. It is a Python `asyncio` daemon that runs continuously in the background, sampling system state, consulting a local LLM, and applying profile changes when warranted.

## Module Structure

```
orchestrator/adaptive_os/
├── core/
│   ├── config.py          # Pydantic settings model
│   ├── orchestrator.py    # Central event loop
│   ├── decision_engine.py # Ollama LLM interface
│   ├── habit_tracker.py   # Usage pattern learning
│   └── state.py           # SQLite persistence
├── detectors/
│   └── context.py         # System state sampler
├── profiles/
│   └── manager.py         # Profile switch executor
├── api/
│   └── server.py          # aiohttp REST API
├── cli.py                 # Click CLI
└── main.py                # Entry point
```

## The Detection Loop

Every `detection.interval` seconds (default: 30), the orchestrator runs one **tick**:

```python
async def _tick(self):
    # 1. Sample system state
    snapshot = await detector.sample(recent_profiles=...)

    # 2. Re-analyse habits every 60 ticks (~30 min)
    if tick_count % 60 == 0:
        asyncio.create_task(habits.analyse())

    # 3. Get habit hint for LLM
    hint = habits.summary.to_llm_hint(hour, dow, apps)

    # 4. Ask LLM which profile fits
    decision = await engine.decide(snapshot, habit_hint=hint)

    # 5. Apply if confident + cooldown elapsed
    if decision.is_actionable and not in_cooldown:
        await manager.switch(decision.profile, ...)
```

## Context Snapshot

The `ContextSnapshot` dataclass captures:

| Field | Source | Example |
|---|---|---|
| `active_apps` | `psutil.process_iter()` | `["code", "alacritty"]` |
| `focused_window` | `hyprctl activewindow` | `"adaptive-os — VSCode"` |
| `cpu_percent` | `psutil.cpu_percent()` | `45.2` |
| `ram_percent` | `psutil.virtual_memory()` | `61.0` |
| `gpu_active` | `/proc/driver/nvidia/` | `false` |
| `gamepad_connected` | `/dev/input/js*` | `false` |
| `external_display` | `hyprctl monitors` | `true` |
| `audio_output` | `pactl get-default-sink` | `"headphones"` |
| `hour` | `datetime.now()` | `14` |
| `day_of_week` | `datetime.now()` | `1` (Tuesday) |
| `is_weekend` | derived | `false` |
| `recent_profiles` | StateDB | `["work", "work"]` |

## LLM Prompt Structure

```
[SYSTEM]
You are the decision engine for an AI-adaptive operating system.
Your task is to analyse the user's current system context...
Respond ONLY with valid JSON: {"profile": "...", "confidence": 0.0-1.0, "reason": "..."}

[USER]
Analyse this system context and decide the best profile:

Time: 14:00 on Tuesday (weekday).
Active applications: alacritty, code, firefox, docker.
Focused window: adaptive-os — VSCode.
CPU: 45%, RAM: 61%.
GPU active: False.
Gamepad connected: False.
Audio output: headphones.
Recent profiles used: work, work, work.

Learned habits:
- At 14:00 on Tuesday, the user is in 'work' mode 87% of the time.
- App 'code' strongly correlates with 'work' profile (94% of past observations).
```

## Decision Engine

- Uses `httpx.AsyncClient` for non-blocking Ollama API calls
- Temperature set to `0.1` for deterministic, consistent outputs
- Parses JSON response; strips markdown fences if model adds them
- Falls back to `confidence=0.0` on any error (safe: no switch happens)

## Profile Switch Execution

`ProfileManager.switch()` runs these steps in sequence:

1. **NixOS rebuild** (if `nix` is available): `nixos-rebuild switch --flake .#<profile>`
2. **Hyprland reload**: symlinks profile config → `hyprctl reload`
3. **Waybar restart**: `pkill waybar` → launch with new config
4. **Theme apply**: runs `ui/themes/<profile>/apply.sh`
5. **systemd target**: `systemctl --user start adaptive-os-<profile>.target`
6. **Desktop notification**: `notify-send` with profile name and reason
7. **State record**: writes to SQLite history

Steps 2–6 run even if NixOS rebuild is unavailable (non-NixOS systems).

## Habit Tracker

The `HabitTracker` analyses `profile_history` and `context_snapshots` tables:

### Time Priors
For each `(hour, day_of_week)` pair, it computes the probability distribution over profiles from the last 30 days. Example:
```python
time_priors[14][1] = {"work": 0.87, "gaming": 0.08, "study": 0.05}
```

### App Correlations
For each app that appears in context snapshots, it computes how often it co-occurs with each profile:
```python
app_correlations["code"] = [("work", 0.94), ("study", 0.04), ...]
```

Only apps with ≥5 observations are used (avoids noise from rarely-seen processes).

### LLM Hint Generation
When confidence-boosting priors exist (≥60% for time, ≥70% for apps), a natural-language hint is appended to the LLM prompt. This nudges the model toward historically accurate decisions without hard-coding rules.

## REST API

All endpoints bind to `127.0.0.1:7979` only.

| Method | Path | Description |
|---|---|---|
| GET | `/status` | Orchestrator state, current profile, habit summary |
| POST | `/switch/{profile}` | Manual profile switch |
| POST | `/ask` | Conversational interface `{"question": "..."}` |
| GET | `/profiles` | List available profiles |
| GET | `/report` | Weekly habit usage report |

## Configuration

`~/.config/adaptive-os/config.yaml`:

```yaml
ollama:
  host: "http://localhost:11434"
  model: "llama3"          # or mistral, phi3, etc.
  timeout: 30
  min_confidence: 0.75     # threshold for automatic switches

detection:
  interval: 30             # seconds between ticks
  switch_cooldown: 120     # minimum seconds between switches
  history_window: 3        # recent snapshots to include

logging:
  level: "INFO"            # DEBUG for verbose output
```

## State Database

SQLite at `~/.local/share/adaptive-os/state.db`:

```sql
profile_history    -- every switch: profile, timestamp, reason, confidence
context_snapshots  -- every tick: full JSON snapshot
kv                 -- key-value store: current_profile, etc.
```

The database grows at ~1 KB/hour under normal usage. The NixOS GC job cleans old entries weekly.
