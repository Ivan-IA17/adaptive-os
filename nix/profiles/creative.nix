{ config, pkgs, lib, ... }:
# Creative profile — content creation, design, audio production
# Activated when: Krita, Blender, OBS, Audacity, DaVinci open
{
  environment.systemPackages = with pkgs; [
    # Visual design
    krita inkscape gimp darktable
    blender

    # Video
    obs-studio davinci-resolve kdenlive
    ffmpeg

    # Audio production
    ardour audacity
    carla  # Audio plugin host
    lsp-plugins

    # Writing
    libreoffice obsidian

    # Screen recording
    wf-recorder
  ];

  # ── PipeWire: studio low-latency ────────────────────────
  services.pipewire = {
    jack.enable = true;
    extraConfig.pipewire."92-studio-latency" = {
      context.properties = {
        default.clock.rate = 48000;
        default.clock.quantum = 64;
        default.clock.min-quantum = 64;
      };
    };
  };

  # ── CPU: performance for rendering ──────────────────────
  powerManagement.cpuFreqGovernor = "performance";

  # ── Colour management ───────────────────────────────────
  services.colord.enable = true;

  # ── Real-time audio permissions ─────────────────────────
  security.pam.loginLimits = [
    { domain = "@audio"; type = "-"; item = "rtprio";  value = "95"; }
    { domain = "@audio"; type = "-"; item = "memlock"; value = "unlimited"; }
  ];
  users.groups.audio = {};
}
