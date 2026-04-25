{ config, pkgs, lib, ... }:
# Work profile — development environment
# Activated when: IDE/editor open, terminal active, coding context detected
{
  # ── Development packages ────────────────────────────────
  environment.systemPackages = with pkgs; [
    # Editors & IDEs
    vscode neovim emacs

    # Terminals
    alacritty kitty

    # Dev tools
    docker docker-compose kubectl helm terraform
    git-lfs lazygit gh
    jq yq ripgrep fd bat eza delta
    nodejs_20 python3 go rustup

    # Browsers
    firefox chromium

    # Communication
    slack discord

    # DB tools
    dbeaver-bin

    # Network tools
    nmap wireshark-qt httpie
  ];

  # ── Services ────────────────────────────────────────────
  virtualisation.docker = {
    enable = true;
    autoPrune.enable = true;
  };

  services = {
    openssh.enable = true;
    syncthing = {
      enable = true;
      user = "ivan";
    };
  };

  # ── CPU: performance governor ───────────────────────────
  powerManagement.cpuFreqGovernor = "performance";

  # ── GPU: integrated preferred ───────────────────────────
  hardware.nvidia.powerManagement.enable = true;

  # ── Systemd targets for this profile ───────────────────
  systemd.user.targets.work = {
    description = "Work profile target";
    wants = [ "docker.service" "syncthing.service" ];
  };
}
