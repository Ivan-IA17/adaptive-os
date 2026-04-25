# Architecture Overview

## Design Philosophy

Adaptive OS follows three core principles:

1. **Declarative everything** — System state is fully described in code (NixOS). Any configuration can be reproduced, versioned and rolled back.
2. **Local AI only** — All inference runs on-device via Ollama. No data leaves the machine.
3. **Progressive enhancement** — The system works without AI (manual profile switching). AI adds automatic adaptation on top.

## Component Map

```
                    ┌──────────────────────────────────────┐
                    │           USER INTERACTIONS           │
                    │  CLI · Rofi overlay · Voice · Hotkey  │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │           REST API (:7979)            │
                    │    /profile  /status  /switch  /ask   │
                    └──────────────┬───────────────────────┘
                                   │
          ┌────────────────────────▼──────────────────────────────┐
          │                  AI ORCHESTRATOR                       │
          │                                                        │
          │  ┌─────────────────┐     ┌──────────────────────────┐ │
          │  │ Context Detector│────▶│    Decision Engine        │ │
          │  │                 │     │    (Ollama LLM)           │ │
          │  │ • process_watch │     │                          │ │
          │  │ • hardware_scan │     │  "Given context X,        │ │
          │  │ • time_sensor   │     │   which profile fits?"    │ │
          │  │ • habit_tracker │     └──────────┬───────────────┘ │
          │  └─────────────────┘                │                  │
          │                          ┌──────────▼───────────────┐ │
          │                          │    Profile Manager        │ │
          │                          │                          │ │
          │                          │  • loads profile spec    │ │
          │                          │  • calls nix switch      │ │
          │                          │  • applies UI configs    │ │
          │                          │  • restarts services     │ │
          │                          └──────────────────────────┘ │
          └───────────────────────────────────────────────────────┘
                    │                           │
          ┌─────────▼──────────┐    ┌───────────▼────────────────┐
          │   NIXOS PROFILES   │    │      UI CONFIGURATION       │
          │                    │    │                             │
          │  work.nix          │    │  hyprland/work.conf        │
          │  gaming.nix        │    │  hyprland/gaming.conf      │
          │  creative.nix      │    │  waybar/work.jsonc         │
          │  server.nix        │    │  themes/dark-focused/      │
          │  study.nix         │    │  rofi/launcher.rasi        │
          └────────────────────┘    └─────────────────────────────┘
```

## Data Flow

### Automatic Context Detection (every 30 seconds)

```
1. Detectors sample the system:
   - Running processes and window titles
   - Connected hardware (GPU, controllers, audio devices)
   - Current time and day of week
   - Historical usage patterns (SQLite db)

2. Context is serialised to a JSON snapshot:
   {
     "active_apps": ["code", "alacritty", "chromium"],
     "window_title": "adaptive-os — VSCode",
     "cpu_load": 0.45,
     "gpu_active": false,
     "audio_output": "headphones",
     "time_hour": 14,
     "day_type": "weekday",
     "recent_profiles": ["work", "work", "work"]
   }

3. LLM prompt is constructed and sent to Ollama:
   "Based on this system context, which profile best fits?
    Respond with JSON: {profile, confidence, reason}"

4. If confidence > 0.75 and profile != current:
   → Profile Manager triggers a switch
```

### Manual Profile Switch

```
adaptive-os switch gaming
  → API call → Profile Manager
  → nix build .#gaming → nix-env activate
  → hyprctl reload gaming.conf
  → waybar restart with gaming.jsonc
  → systemd profile target switch
```

### Conversational Interface

```
adaptive-os "I need to record a podcast"
  → LLM analyses intent
  → Maps to: creative profile + audio_production variant
  → Switches profile
  → Launches: OBS, Audacity, sets audio routing
  → Reports: "Switched to Creative mode. Launched OBS and Audacity."
```

## Key Design Decisions

### Why NixOS?

NixOS stores the entire system configuration as immutable, reproducible Nix expressions. This means:
- Profile switching = loading a different Nix expression. Atomic, rollbackable.
- No partial states. The system is always in a known configuration.
- Profiles can be version-controlled alongside application code.

### Why Ollama (local LLM)?

- Zero latency from network calls
- No telemetry or data leaving the device
- Works offline
- Model can be swapped (llama3, mistral, phi3, custom fine-tune)

### Why Hyprland?

- Scriptable via IPC socket (`hyprctl`)
- Hot-reloadable config without restarting compositor
- Per-workspace and per-window rules ideal for profile variants
- Native Wayland, low overhead

## State Machine

```
         ┌─────────┐
    ┌────▶│  IDLE   │◀────────────────┐
    │     └────┬────┘                 │
    │          │ context change       │
    │     ┌────▼──────────┐           │
    │     │  ANALYSING    │           │
    │     │  (LLM call)   │           │
    │     └────┬──────────┘           │
    │          │ decision made        │
    │     ┌────▼──────────┐           │
    │     │   SWITCHING   │           │
    │     │  (nix + ui)   │           │
    │     └────┬──────────┘           │
    │          │ switch complete      │
    └──────────┘ cooldown (120s) ─────┘
```

## Security Model

- The orchestrator runs as the user, not root
- NixOS profile switching uses `nix-env` and systemd user units (no sudo)
- The REST API binds to `127.0.0.1` only
- The LLM has no network access, no tool use — it only classifies context
- All profile configs are reviewed by the user before deployment
