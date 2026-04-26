#!/usr/bin/env bash
# Apply WORK theme — dark focused, blue accents

GTK_THEME="adw-gtk3-dark"
ICON_THEME="Papirus-Dark"
CURSOR_THEME="Bibata-Modern-Classic"
FONT="Inter 10"
MONO_FONT="JetBrainsMono Nerd Font 10"
ACCENT="#1565C0"

# GTK3 via gsettings
gsettings set org.gnome.desktop.interface gtk-theme        "$GTK_THEME"
gsettings set org.gnome.desktop.interface icon-theme       "$ICON_THEME"
gsettings set org.gnome.desktop.interface cursor-theme     "$CURSOR_THEME"
gsettings set org.gnome.desktop.interface font-name        "$FONT"
gsettings set org.gnome.desktop.interface monospace-font-name "$MONO_FONT"
gsettings set org.gnome.desktop.interface color-scheme     "prefer-dark"

# GTK4 / libadwaita accent colour
gsettings set org.gnome.desktop.interface accent-color     "blue"

# Qt via kvantum
if command -v kvantummanager &>/dev/null; then
    kvantummanager --set KvGnomeDark
fi

# Alacritty terminal — dark theme
ALACRITTY_CONF="$HOME/.config/alacritty/alacritty.toml"
if [ -f "$ALACRITTY_CONF" ]; then
    sed -i 's/^import = .*/import = ["~\/.config\/alacritty\/themes\/work.toml"]/' "$ALACRITTY_CONF"
fi

# Reload GTK apps (soft reload via dconf)
dconf reset -f /org/gnome/ 2>/dev/null || true

echo "Work theme applied."
