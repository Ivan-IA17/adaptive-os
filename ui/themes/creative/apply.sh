#!/usr/bin/env bash
# Apply CREATIVE theme — neutral grey, colour-accurate, minimal chrome

GTK_THEME="adw-gtk3-dark"
ICON_THEME="Papirus"
CURSOR_THEME="Bibata-Modern-Classic"
FONT="Inter 11"

gsettings set org.gnome.desktop.interface gtk-theme     "$GTK_THEME"
gsettings set org.gnome.desktop.interface icon-theme    "$ICON_THEME"
gsettings set org.gnome.desktop.interface cursor-theme  "$CURSOR_THEME"
gsettings set org.gnome.desktop.interface font-name     "$FONT"
gsettings set org.gnome.desktop.interface color-scheme  "prefer-dark"
gsettings set org.gnome.desktop.interface accent-color  "purple"

# Disable blue-light filter for colour accuracy
pkill wlsunset 2>/dev/null || true

# Load ICC colour profile if available
ICC_PROFILE="$HOME/.local/share/icc/srgb.icc"
if [ -f "$ICC_PROFILE" ] && command -v dispwin &>/dev/null; then
    dispwin -d 1 "$ICC_PROFILE"
fi

# Re-enable notifications for render completion alerts
dunstctl set-paused false

echo "Creative theme applied."
