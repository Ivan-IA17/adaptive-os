#!/usr/bin/env bash
# Apply STUDY theme — warm light, reduced eye strain

GTK_THEME="adw-gtk3"
ICON_THEME="Papirus-Light"
CURSOR_THEME="Bibata-Modern-Classic"
FONT="Inter 11"

gsettings set org.gnome.desktop.interface gtk-theme     "$GTK_THEME"
gsettings set org.gnome.desktop.interface icon-theme    "$ICON_THEME"
gsettings set org.gnome.desktop.interface cursor-theme  "$CURSOR_THEME"
gsettings set org.gnome.desktop.interface font-name     "$FONT"
gsettings set org.gnome.desktop.interface color-scheme  "prefer-light"
gsettings set org.gnome.desktop.interface accent-color  "green"
gsettings set org.gnome.desktop.interface text-scaling-factor 1.1

# Warm colour temperature — coordinates: Sevilla, España
pkill wlsunset 2>/dev/null || true
wlsunset -t 4200 -T 6500 -l 37.3 -L -5.9 &

# Suppress all non-critical notifications
dunstctl set-paused false
# (dunst study config handles filtering)

echo "Study theme applied."
