#!/usr/bin/env bash
# Apply SERVER theme — minimal, terminal-focused

GTK_THEME="adw-gtk3-dark"
ICON_THEME="Papirus-Dark"
CURSOR_THEME="Bibata-Modern-Classic"
FONT="JetBrainsMono Nerd Font 10"

gsettings set org.gnome.desktop.interface gtk-theme     "$GTK_THEME"
gsettings set org.gnome.desktop.interface icon-theme    "$ICON_THEME"
gsettings set org.gnome.desktop.interface cursor-theme  "$CURSOR_THEME"
gsettings set org.gnome.desktop.interface font-name     "$FONT"
gsettings set org.gnome.desktop.interface color-scheme  "prefer-dark"
gsettings set org.gnome.desktop.interface accent-color  "slate"

# Only critical system alerts
dunstctl set-paused false

echo "Server theme applied."
