{ config, pkgs, lib, ... }:
# Gaming profile — maximum performance, full-screen experience
# Activated when: gamepad connected, Steam/Lutris/game process detected
{
  # ── Gaming packages ─────────────────────────────────────
  environment.systemPackages = with pkgs; [
    steam steam-run
    lutris heroic
    mangohud goverlay
    gamemode
    discord
    obs-studio
    # Performance monitoring
    nvtopPackages.full
    gpustat
  ];

  # ── Steam ────────────────────────────────────────────────
  programs.steam = {
    enable = true;
    remotePlay.openFirewall = true;
    dedicatedServer.openFirewall = true;
  };

  # ── Gamemode daemon ──────────────────────────────────────
  programs.gamemode = {
    enable = true;
    settings = {
      general = {
        reaper_freq = 5;
        desiredgov = "performance";
        softrealtime = "auto";
        renice = 10;
      };
      gpu = {
        apply_gpu_optimisations = "accept-responsibility";
        gpu_device = 0;
        nv_powermizer_mode = 1;  # Maximum performance
        amd_performance_level = "high";
      };
      custom = {
        start = "${pkgs.libnotify}/bin/notify-send 'GameMode' 'Performance mode ON'";
        end   = "${pkgs.libnotify}/bin/notify-send 'GameMode' 'Performance mode OFF'";
      };
    };
  };

  # ── CPU: always performance ──────────────────────────────
  powerManagement.cpuFreqGovernor = "performance";

  # ── GPU: NVIDIA maximum performance ─────────────────────
  hardware.nvidia = {
    powerManagement.enable = false;  # Disable power saving
    forceFullCompositionPipeline = true;
  };

  # ── Disable unnecessary services ────────────────────────
  systemd.services = {
    syncthing.enable = lib.mkForce false;
    docker.enable = lib.mkForce false;
  };

  # ── PipeWire: low-latency gaming audio ──────────────────
  services.pipewire.extraConfig.pipewire."92-low-latency" = {
    context.properties = {
      default.clock.rate = 48000;
      default.clock.quantum = 32;
      default.clock.min-quantum = 32;
      default.clock.max-quantum = 32;
    };
  };

  # ── Kernel: gaming optimisations ────────────────────────
  boot.kernel.sysctl = {
    "vm.swappiness" = 10;
    "kernel.sched_cfs_bandwidth_slice_us" = 3000;
  };
}
