{ config, pkgs, lib, ... }:
# Study profile — reading, note-taking, focused learning
# Activated when: PDF reader, Anki, Obsidian, academic content detected
{
  environment.systemPackages = with pkgs; [
    # Notes & reading
    obsidian zotero evince okular
    calibre

    # Flashcards
    anki

    # Browser (extensions for research)
    firefox

    # Writing
    libreoffice texlive.combined.scheme-full
    pandoc

    # Pomodoro / focus
    gnome-pomodoro
  ];

  # ── CPU: powersave to reduce fan noise ──────────────────
  powerManagement.cpuFreqGovernor = "powersave";

  # ── Display: warmer colour temperature ──────────────────
  # Handled by the UI layer (wlsunset via Hyprland)

  # ── Notifications: all blocked except alarms ─────────────
  # Handled by dunst config in ui/themes/study/dunstrc
}
