#!/usr/bin/env bash
# Apply GAMING theme — dark, vibrant purple/red accents

GTK_THEME="adw-gtk3-dark"
ICON_THEME="Papirus-Dark"
CURSOR_THEME="Bibata-Modern-Amber"
FONT="Inter 10"

gsettings set org.gnome.desktop.interface gtk-theme     "$GTK_THEME"
gsettings set org.gnome.desktop.interface icon-theme    "$ICON_THEME"
gsettings set org.gnome.desktop.interface cursor-theme  "$CURSOR_THEME"
gsettings set org.gnome.desktop.interface font-name     "$FONT"
gsettings set org.gnome.desktop.interface color-scheme  "prefer-dark"
gsettings set org.gnome.desktop.interface accent-color  "purple"

# Enable MangoHud overlay for all Vulkan/OpenGL apps
export MANGOHUD=1
echo "export MANGOHUD=1" > /tmp/adaptive-os-env-gaming.sh

# Mute all notifications
dunstctl set-paused true

echo "Gaming theme applied."
