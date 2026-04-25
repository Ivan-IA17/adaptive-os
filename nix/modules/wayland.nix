{ config, pkgs, inputs, ... }:
# Wayland / Hyprland compositor module
{
  # ── Hyprland ────────────────────────────────────────────
  programs.hyprland = {
    enable = true;
    package = inputs.hyprland.packages.${pkgs.system}.hyprland;
    xwayland.enable = true;
  };

  # ── XDG portals ─────────────────────────────────────────
  xdg.portal = {
    enable = true;
    extraPortals = [ pkgs.xdg-desktop-portal-hyprland ];
  };

  # ── Login manager ───────────────────────────────────────
  services.greetd = {
    enable = true;
    settings.default_session = {
      command = "${pkgs.greetd.tuigreet}/bin/tuigreet --time --cmd Hyprland";
      user = "greeter";
    };
  };

  # ── Wayland-compatible packages ─────────────────────────
  environment.systemPackages = with pkgs; [
    hyprpaper        # Wallpaper daemon
    hyprlock         # Screen locker
    waybar           # Status bar
    rofi-wayland     # App launcher
    dunst            # Notification daemon
    wl-clipboard     # Clipboard
    grim slurp       # Screenshots
    brightnessctl    # Brightness control
    playerctl        # Media control
    pavucontrol      # Audio control GUI
  ];

  # ── Environment variables for Wayland ───────────────────
  environment.sessionVariables = {
    NIXOS_OZONE_WL = "1";       # Electron apps use Wayland
    MOZ_ENABLE_WAYLAND = "1";   # Firefox Wayland
    QT_QPA_PLATFORM = "wayland";
    GDK_BACKEND = "wayland";
    XDG_SESSION_TYPE = "wayland";
    XDG_CURRENT_DESKTOP = "Hyprland";
  };

  # ── Fonts ───────────────────────────────────────────────
  fonts = {
    enableDefaultPackages = true;
    packages = with pkgs; [
      noto-fonts noto-fonts-cjk noto-fonts-emoji
      (nerdfonts.override { fonts = [ "JetBrainsMono" "FiraCode" ]; })
      inter
    ];
    fontconfig.defaultFonts = {
      serif = [ "Noto Serif" ];
      sansSerif = [ "Inter" ];
      monospace = [ "JetBrainsMono Nerd Font" ];
    };
  };
}
