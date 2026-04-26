#!/usr/bin/env bash
# Rofi script mode for Adaptive OS profile switching
# Usage: rofi -show adaptive-os -modi "adaptive-os:$(which rofi-profile-switcher.sh)"

PROFILES=("🖥️ work" "🎮 gaming" "🎨 creative" "🖧 server" "📖 study")

if [ -z "$@" ]; then
    # Print options for Rofi to display
    for p in "${PROFILES[@]}"; do
        echo "$p"
    done
else
    # User selected an option — extract profile name and switch
    SELECTED="$@"
    PROFILE=$(echo "$SELECTED" | awk '{print $2}')
    if [ -n "$PROFILE" ]; then
        adaptive-os switch "$PROFILE" && \
        notify-send -i system-run -t 2000 "Adaptive OS" "Switching to $SELECTED..."
    fi
fi
