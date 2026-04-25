# Installation Guide

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| NixOS | 24.05+ | Or any Linux with Nix flakes enabled |
| Ollama | latest | For local LLM inference |
| Python | 3.11+ | For the orchestrator daemon |
| Hyprland | 0.40+ | Recommended compositor |
| RAM | 16 GB | 8 GB minimum (LLM needs ~4–8 GB) |

## Step 1 — Install NixOS

Download NixOS from [nixos.org/download](https://nixos.org/download).

Enable flakes in your `configuration.nix`:

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

## Step 2 — Clone the repository

```bash
git clone https://github.com/Ivan-IA17/adaptive-os
cd adaptive-os
```

## Step 3 — Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
systemctl enable --now ollama
ollama pull llama3
```

## Step 4 — Install the Python orchestrator

```bash
cd orchestrator
pip install -e ".[dev]"
```

## Step 5 — Apply NixOS configuration

```bash
# Copy the base configuration
sudo cp nix/configuration.nix /etc/nixos/

# Rebuild
sudo nixos-rebuild switch
```

## Step 6 — Start the AI daemon

```bash
# Start as a systemd user service
systemctl --user enable --now adaptive-os-orchestrator

# Or run manually for testing
adaptive-os start --verbose
```

## Step 7 — Verify

```bash
adaptive-os status
# Expected output:
# ✅ Orchestrator: running (PID 1234)
# ✅ Ollama: connected (llama3)
# ✅ Current profile: work
# ✅ Context detection: active
```

## Troubleshooting

### Ollama not responding
```bash
systemctl status ollama
ollama serve  # start manually
```

### Profile switch fails
```bash
adaptive-os logs --last 50
nix build .#profiles.work  # test nix build manually
```

### High CPU usage
The orchestrator polls every 30 seconds by default. Increase the interval:
```bash
adaptive-os config set detection.interval 60
```
