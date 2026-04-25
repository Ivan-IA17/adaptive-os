# 🧠 Adaptive OS

> An AI-driven operating system layer that dynamically adapts to any user context using local LLMs.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![NixOS](https://img.shields.io/badge/base-NixOS-5277C3?logo=nixos)](https://nixos.org)
[![Ollama](https://img.shields.io/badge/AI-Ollama-black)](https://ollama.com)
[![Python](https://img.shields.io/badge/orchestrator-Python%203.11+-3776AB?logo=python)](https://python.org)

## What is Adaptive OS?

Adaptive OS is not a new kernel — it is an **intelligent orchestration layer** built on top of NixOS that uses a local LLM (via Ollama) to continuously monitor user behaviour and automatically reconfigure the entire system to match the current activity.

When you open VSCode, terminals and GitHub — the system switches to **Developer mode**: activates Docker, sets focused keybindings, applies a dark minimal theme and silences notifications.

When you plug in a gamepad — it switches to **Gaming mode**: enables GPU performance profiles, launches Steam, sets a full-screen compositor layout and disables all background services.

You can also simply **tell the OS what you want to do** and it reconfigures itself completely.

## Key Features

| Feature | Description |
|---|---|
| 🤖 **AI Context Detection** | Local LLM analyses open apps, hardware, time and habits |
| ⚡ **Instant Profile Switching** | NixOS declarative configs swap in seconds |
| 🎨 **Dynamic UI** | Hyprland compositor, Waybar and themes all change per profile |
| 💬 **Conversational Interface** | Tell the OS what you need in natural language |
| 🔒 **100% Local AI** | All inference runs on-device via Ollama — no cloud, no telemetry |
| 📚 **Fully Documented** | Every module documented, architecture explained |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│   Hyprland  ·  Waybar  ·  Rofi  ·  CLI  ·  Voice       │
├─────────────────────────────────────────────────────────┤
│                  AI ORCHESTRATOR                         │
│   Context Detector → Decision Engine → Profile Manager  │
│              (Python daemon + Ollama)                    │
├──────────────┬──────────────┬──────────────┬────────────┤
│   WORK       │   GAMING     │  CREATIVE    │  SERVER    │
│   profile    │   profile    │  profile     │  profile   │
├─────────────────────────────────────────────────────────┤
│              NIXOS DECLARATIVE BASE                      │
│         Kernel · Drivers · Systemd · Wayland            │
└─────────────────────────────────────────────────────────┘
```

## Profiles

- **🖥️ Work** — VSCode, terminals, Docker, focused layout, dark theme
- **🎮 Gaming** — GPU performance, Steam, full-screen compositor, no background services
- **🎨 Creative** — Colour-accurate display, Krita/Blender, audio production stack
- **🖧 Server** — Headless or minimal UI, monitoring tools, network services
- **📖 Study** — Reading mode, note-taking apps, Pomodoro timer, soft lighting

## Quick Start

```bash
# 1. Install NixOS (see docs/guides/installation.md)
# 2. Clone this repository
git clone https://github.com/Ivan-IA17/adaptive-os
cd adaptive-os

# 3. Install Ollama and pull a model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3

# 4. Install the orchestrator
pip install -e orchestrator/

# 5. Start the AI daemon
adaptive-os start

# 6. Talk to your OS
adaptive-os "I want to work on a Python project"
```

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture/overview.md) | Full system design and component interaction |
| [Profiles](docs/architecture/profiles.md) | How profiles work and how to create custom ones |
| [Orchestrator](docs/architecture/orchestrator.md) | AI decision engine internals |
| [NixOS Setup](docs/guides/nixos-setup.md) | Installing and configuring the NixOS base |
| [Installation](docs/guides/installation.md) | Step-by-step installation guide |
| [Contributing](docs/guides/contributing.md) | How to contribute to the project |

## Project Structure

```
adaptive-os/
├── nix/                    # NixOS declarative configuration
│   ├── profiles/           # Per-mode system configurations
│   ├── modules/            # Reusable NixOS modules
│   └── overlays/           # Package overlays
├── orchestrator/           # AI daemon (Python)
│   ├── core/               # Main loop, config, logging
│   ├── detectors/          # Context sensors (apps, hw, time, habits)
│   ├── profiles/           # Profile definitions and switcher
│   └── api/                # REST API for CLI and UI
├── ui/                     # UI configuration files
│   ├── hyprland/           # Compositor configs per profile
│   ├── waybar/             # Status bar configs
│   ├── themes/             # GTK/Qt/terminal themes
│   └── rofi/               # App launcher configs
├── cli/                    # adaptive-os command-line tool
├── scripts/                # Install and utility scripts
├── tests/                  # Unit and integration tests
└── docs/                   # Full documentation
```

## Requirements

- NixOS 24.05+ (or any Linux with Nix installed)
- Ollama with llama3 or mistral model
- Python 3.11+
- Wayland compositor (Hyprland recommended)
- 8GB RAM minimum (16GB recommended for AI inference)

## License

MIT — see [LICENSE](LICENSE)

---

*Built with ❤️ using NixOS, Ollama, Python and Hyprland*
