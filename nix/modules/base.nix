{ config, pkgs, lib, profileName, ... }:
# Base NixOS module shared across ALL profiles.
# Profile-specific modules layer on top of this.
{
  # ── Boot ────────────────────────────────────────────────
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;
  boot.kernelPackages = pkgs.linuxPackages_latest;

  # ── Networking ──────────────────────────────────────────
  networking.networkmanager.enable = true;
  networking.firewall.enable = true;

  # ── Locale ──────────────────────────────────────────────
  time.timeZone = "Europe/Madrid";
  i18n.defaultLocale = "es_ES.UTF-8";

  # ── Sound (PipeWire) ────────────────────────────────────
  sound.enable = false;  # Use PipeWire exclusively
  hardware.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    jack.enable = true;
  };

  # ── Base packages (always present) ──────────────────────
  environment.systemPackages = with pkgs; [
    git curl wget vim htop
    python3 python3Packages.pip
    # Adaptive OS orchestrator dependencies
    python3Packages.psutil
    python3Packages.aiohttp
    python3Packages.pyyaml
    python3Packages.click
    python3Packages.rich
  ];

  # ── Adaptive OS systemd service ─────────────────────────
  systemd.user.services.adaptive-os-orchestrator = {
    description = "Adaptive OS AI Orchestrator";
    wantedBy = [ "graphical-session.target" ];
    after = [ "graphical-session.target" "ollama.service" ];
    serviceConfig = {
      ExecStart = "${pkgs.python3}/bin/python3 -m adaptive_os.main";
      Restart = "on-failure";
      RestartSec = "5s";
      Environment = [
        "ADAPTIVE_OS_PROFILE=${profileName}"
        "OLLAMA_HOST=http://localhost:11434"
      ];
    };
  };

  # ── Ollama service ──────────────────────────────────────
  services.ollama = {
    enable = true;
    acceleration = "cuda";  # Change to "rocm" for AMD GPUs
  };

  # ── Security ────────────────────────────────────────────
  security.sudo.wheelNeedsPassword = true;
  services.openssh.enable = lib.mkDefault false;

  # ── Nix settings ────────────────────────────────────────
  nix.settings = {
    experimental-features = [ "nix-command" "flakes" ];
    auto-optimise-store = true;
  };
  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "--delete-older-than 30d";
  };

  system.stateVersion = "24.05";
}
