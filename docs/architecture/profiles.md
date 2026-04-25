# Profile System

## What is a Profile?

A profile is a complete, self-contained description of how the system should behave for a specific activity context. It defines:

- Which packages are installed and active
- Which systemd services run
- How the desktop looks and behaves
- Which keybindings are active
- Resource allocation priorities

## Built-in Profiles

### 🖥️ Work

**Trigger context:** VSCode/Vim/IDE open, terminal active, GitHub/GitLab in browser

| Setting | Value |
|---|---|
| DE layout | Tiling, 2-column master |
| Theme | Dark focused (no distractions) |
| Services | Docker, SSH agent, syncthing |
| Notifications | Critical only |
| CPU governor | `performance` |
| GPU | Integrated only (saves power) |
| Audio | Headphones or speakers (auto) |

### 🎮 Gaming

**Trigger context:** Gamepad connected OR Steam/Lutris/game process detected

| Setting | Value |
|---|---|
| DE layout | Single full-screen workspace |
| Theme | Gaming dark |
| Services | Stop Docker, syncthing, dropbox. Start MangoHud, Gamescope |
| Notifications | All disabled |
| CPU governor | `performance` |
| GPU | Dedicated, max performance profile |
| Audio | Gaming headset preset |

### 🎨 Creative

**Trigger context:** Krita, Blender, Inkscape, OBS, Audacity, DaVinci open

| Setting | Value |
|---|---|
| DE layout | Single large workspace, floating |
| Theme | Neutral grey (colour accuracy) |
| Services | PipeWire low-latency, JACK, colour management daemon |
| Notifications | Disabled |
| CPU governor | `performance` |
| GPU | Dedicated, OpenGL/Vulkan priority |
| Audio | Studio preset (flat EQ) |

### 🖧 Server

**Trigger context:** Time is night, or user ran `adaptive-os switch server`

| Setting | Value |
|---|---|
| DE layout | Minimal / headless option |
| Theme | Terminal only |
| Services | nginx, postgresql, monitoring stack |
| Notifications | Alert-level only |
| CPU governor | `schedutil` |
| GPU | Disabled / minimal |
| Audio | Muted |

### 📖 Study

**Trigger context:** PDF reader, Anki, Obsidian, browser with academic content

| Setting | Value |
|---|---|
| DE layout | Single window focus mode |
| Theme | Warm light theme (easier on eyes) |
| Services | Pomodoro timer, focus blocker |
| Notifications | Disabled |
| CPU governor | `powersave` |
| GPU | Integrated |
| Audio | Focus music / white noise |

## Profile File Format

Each profile is defined in two places:

### 1. NixOS configuration (`nix/profiles/<name>.nix`)

```nix
# nix/profiles/work.nix
{ config, pkgs, ... }:
{
  # Packages active in this profile
  environment.systemPackages = with pkgs; [
    vscode docker git alacritty firefox
    kubectl helm terraform
  ];

  # Services
  services.docker.enable = true;
  services.openssh.enable = true;
  services.syncthing.enable = true;

  # Power management
  powerManagement.cpuFreqGovernor = "performance";

  # Audio
  services.pipewire.enable = true;
}
```

### 2. Orchestrator profile spec (`orchestrator/profiles/<name>.yaml`)

```yaml
# orchestrator/profiles/work.yaml
name: work
display_name: "Work"
icon: "🖥️"
color: "#1565C0"

detection:
  apps:
    match_any: [code, vim, nvim, alacritty, kitty, jetbrains]
    weight: 0.8
  browser_title:
    match_any: [github, gitlab, stackoverflow, docs]
    weight: 0.4
  hardware:
    gamepad_connected: false
  time:
    preferred_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

actions:
  nix_profile: work
  hyprland_config: ui/hyprland/work.conf
  waybar_config: ui/waybar/work.jsonc
  theme: ui/themes/dark-focused
  launch_apps: []
  stop_services: [gaming-audio, mangohud]
  start_services: [docker, syncthing, ssh-agent]

notification_level: critical
auto_lock_minutes: 30
```

## Creating a Custom Profile

1. Create `nix/profiles/myprofile.nix`
2. Create `orchestrator/profiles/myprofile.yaml`
3. Create `ui/hyprland/myprofile.conf`
4. Create `ui/waybar/myprofile.jsonc` (optional)
5. Run `adaptive-os reload` to pick up changes

The AI will automatically consider your new profile when making decisions.

## Profile Switching Lifecycle

```
switch_to("gaming")
  ├── 1. Validate profile exists
  ├── 2. Run pre-switch hooks (save current state)
  ├── 3. nix build .#profiles.gaming
  ├── 4. nix-env --set-flag priority 0 gaming
  ├── 5. systemctl --user start gaming.target
  ├── 6. hyprctl reload ui/hyprland/gaming.conf
  ├── 7. pkill waybar && waybar -c ui/waybar/gaming.jsonc &
  ├── 8. apply_theme("gaming-dark")
  ├── 9. Run post-switch hooks (launch apps, notifications)
  └── 10. Update state db → current_profile = "gaming"
```
