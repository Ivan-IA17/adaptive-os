# NixOS Setup Guide

## Why NixOS?

NixOS stores the entire system configuration as immutable, reproducible Nix expressions. For Adaptive OS this means:

- **Profile switching** = activating a different Nix expression. Atomic, instant rollback.
- **No partial states** — the system is always in a known, consistent configuration.
- **Version-controlled** — your entire OS setup lives in git alongside application code.

## Prerequisites

- NixOS 24.05+ (fresh install or existing system)
- At least 8 GB RAM (16 GB recommended for LLM inference)
- NVIDIA or AMD GPU recommended for faster inference

## Step 1 — Enable Flakes

Add to `/etc/nixos/configuration.nix`:

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

Rebuild:
```bash
sudo nixos-rebuild switch
```

## Step 2 — Clone Adaptive OS

```bash
git clone https://github.com/Ivan-IA17/adaptive-os ~/adaptive-os
cd ~/adaptive-os
```

## Step 3 — Review and Customise

Edit `nix/modules/base.nix` to set your username and timezone:

```nix
time.timeZone = "Europe/Madrid";  # Change to your timezone
i18n.defaultLocale = "es_ES.UTF-8";
```

Edit `nix/modules/base.nix` for GPU type:

```nix
services.ollama.acceleration = "cuda";   # NVIDIA
# services.ollama.acceleration = "rocm"; # AMD
# services.ollama.acceleration = null;   # CPU only
```

## Step 4 — Apply the Initial Profile

Start with the `work` profile:

```bash
sudo nixos-rebuild switch --flake ~/adaptive-os/nix#work
```

This will:
- Install all packages defined in `nix/profiles/work.nix` and `nix/modules/base.nix`
- Enable the Ollama service
- Enable the Hyprland compositor
- Set up the login manager (greetd)

This may take 10–30 minutes on the first run as Nix downloads packages.

## Step 5 — Install the Python Orchestrator

```bash
pip install --user -e ~/adaptive-os/orchestrator/
```

## Step 6 — Pull the AI Model

```bash
ollama pull llama3
# Alternatively, for lower RAM usage:
# ollama pull phi3
# ollama pull mistral
```

## Step 7 — Start Adaptive OS

```bash
# Enable as a systemd user service (starts automatically with your session)
systemctl --user enable --now adaptive-os.service

# Or start manually
adaptive-os start
```

## Step 8 — Verify

```bash
adaptive-os status
```

Expected output:
```
╭─────────────────────────────╮
│   Adaptive OS Status        │
│   🖥️ WORK                   │
│   Running: yes              │
│   Model: llama3             │
│   Detection interval: 30s   │
│   Recent profiles: work     │
╰─────────────────────────────╯
```

## Switching Profiles Manually

```bash
adaptive-os switch gaming
adaptive-os switch creative
adaptive-os switch study
adaptive-os switch server
```

## Rebuilding After Profile Changes

If you modify any `.nix` files:

```bash
sudo nixos-rebuild switch --flake ~/adaptive-os/nix#work
# The AI orchestrator handles this automatically on profile switches
```

## Rollback

NixOS keeps all previous generations. To roll back:

```bash
sudo nixos-rebuild switch --rollback
# Or select from the boot menu at startup
```

## Troubleshooting

### Ollama not starting
```bash
systemctl status ollama
journalctl -u ollama -f
# Restart:
systemctl restart ollama
```

### Hyprland not starting
```bash
journalctl --user -u graphical-session -f
# Check hyprland logs:
cat /tmp/hypr/$(ls /tmp/hypr)/hyprland.log | tail -50
```

### Profile switch fails
```bash
adaptive-os logs
# Try manual nix build:
nix build ~/adaptive-os/nix#profiles.work
```

### High memory usage from Ollama
Use a smaller model:
```bash
ollama pull phi3       # ~2 GB VRAM
ollama pull mistral    # ~4 GB VRAM
ollama pull llama3     # ~8 GB VRAM

# Update config:
adaptive-os config set ollama.model phi3
```
