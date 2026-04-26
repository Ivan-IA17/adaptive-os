#!/usr/bin/env bash
# Adaptive OS — Automated installer
# Supports: NixOS, Arch Linux, Ubuntu/Debian
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$HOME/.local/share/adaptive-os"
CONFIG_DIR="$HOME/.config/adaptive-os"

log()  { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }
info() { echo -e "${BLUE}→${NC} $*"; }

banner() {
    echo -e "${BOLD}"
    echo "  ╔═══════════════════════════════════════╗"
    echo "  ║       🧠 ADAPTIVE OS INSTALLER        ║"
    echo "  ║    AI-driven system orchestrator       ║"
    echo "  ╚═══════════════════════════════════════╝"
    echo -e "${NC}"
}

detect_os() {
    if [ -f /etc/nixos/configuration.nix ]; then echo "nixos"
    elif command -v pacman &>/dev/null; then echo "arch"
    elif command -v apt-get &>/dev/null; then echo "debian"
    else echo "unknown"; fi
}

check_requirements() {
    info "Checking requirements..."
    local missing=()

    command -v python3 &>/dev/null || missing+=("python3")
    command -v git     &>/dev/null || missing+=("git")
    command -v curl    &>/dev/null || missing+=("curl")

    if [ ${#missing[@]} -gt 0 ]; then
        err "Missing required tools: ${missing[*]}. Please install them first."
    fi

    PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
        log "Python $PYTHON_VER"
    else
        err "Python 3.11+ required (found $PYTHON_VER)"
    fi
}

install_ollama() {
    if command -v ollama &>/dev/null; then
        log "Ollama already installed ($(ollama --version 2>/dev/null || echo 'version unknown'))"
        return
    fi
    info "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    log "Ollama installed"
}

pull_model() {
    local model="${ADAPTIVE_OS_MODEL:-llama3}"
    info "Pulling LLM model: $model (this may take a few minutes)..."
    if ollama list 2>/dev/null | grep -q "$model"; then
        log "Model '$model' already available"
    else
        ollama pull "$model"
        log "Model '$model' pulled"
    fi
}

install_python_package() {
    info "Installing Adaptive OS Python package..."
    pip3 install --user -e "$REPO_DIR/orchestrator/" \
        --quiet --no-warn-script-location
    log "Python package installed"
}

install_system_deps_arch() {
    info "Installing system dependencies (Arch)..."
    sudo pacman -Sy --needed --noconfirm \
        hyprland waybar rofi-wayland dunst \
        wlsunset hyprpaper hyprlock \
        python-psutil python-aiohttp python-yaml \
        pipewire pipewire-pulse wireplumber \
        gtk3 gtk4 libadwaita papirus-icon-theme \
        brightnessctl playerctl wl-clipboard \
        grim slurp
    log "Arch dependencies installed"
}

install_system_deps_debian() {
    info "Installing system dependencies (Debian/Ubuntu)..."
    sudo apt-get update -qq
    sudo apt-get install -y \
        python3-pip python3-psutil \
        pipewire pipewire-pulse wireplumber \
        libgtk-3-dev libgtk-4-dev \
        brightnessctl playerctl wl-clipboard \
        grim slurp dunst
    warn "Hyprland and Waybar on Debian/Ubuntu require manual setup."
    warn "See: https://github.com/Ivan-IA17/adaptive-os/blob/main/docs/guides/nixos-setup.md"
    log "Debian dependencies installed (partial)"
}

create_directories() {
    info "Creating data directories..."
    mkdir -p "$DATA_DIR" "$CONFIG_DIR"
    mkdir -p "$HOME/.config/hypr"
    mkdir -p "$HOME/.config/waybar"
    mkdir -p "$HOME/.config/alacritty/themes"
    log "Directories created"
}

create_default_config() {
    local cfg="$CONFIG_DIR/config.yaml"
    if [ -f "$cfg" ]; then
        warn "Config already exists at $cfg, skipping."
        return
    fi
    info "Creating default configuration..."
    cat > "$cfg" <<'YAML'
ollama:
  host: "http://localhost:11434"
  model: "llama3"
  timeout: 30
  min_confidence: 0.75

detection:
  interval: 30
  switch_cooldown: 120
  history_window: 3

logging:
  level: "INFO"
YAML
    log "Default config created at $cfg"
}

install_systemd_service() {
    info "Installing systemd user service..."
    local service_dir="$HOME/.config/systemd/user"
    mkdir -p "$service_dir"

    ORCHESTRATOR_BIN=$(python3 -c "import shutil; print(shutil.which('adaptive-os') or '')")
    if [ -z "$ORCHESTRATOR_BIN" ]; then
        ORCHESTRATOR_BIN="$HOME/.local/bin/adaptive-os"
    fi

    cat > "$service_dir/adaptive-os.service" <<EOF
[Unit]
Description=Adaptive OS AI Orchestrator
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$ORCHESTRATOR_BIN start --verbose
Restart=on-failure
RestartSec=5s
Environment=ADAPTIVE_OS_ROOT=$REPO_DIR

[Install]
WantedBy=graphical-session.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable adaptive-os.service
    log "Systemd service installed and enabled"
}

symlink_hyprland_config() {
    info "Setting up Hyprland config symlink..."
    local hypr_dir="$HOME/.config/hypr"
    local work_conf="$REPO_DIR/ui/hyprland/work.conf"

    # Only symlink if no existing hyprland config
    if [ ! -f "$hypr_dir/hyprland.conf" ]; then
        ln -sf "$work_conf" "$hypr_dir/hyprland.conf"
        log "Hyprland config symlinked (work profile)"
    else
        warn "Existing hyprland.conf found, not overwriting."
        warn "To use Adaptive OS profiles, back it up and run:"
        warn "  ln -sf $work_conf ~/.config/hypr/hyprland.conf"
    fi
}

print_summary() {
    echo ""
    echo -e "${BOLD}${GREEN}Installation complete!${NC}"
    echo ""
    echo "  Repo:    $REPO_DIR"
    echo "  Config:  $CONFIG_DIR/config.yaml"
    echo "  Data:    $DATA_DIR"
    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    echo "  1. Start Ollama:           ollama serve"
    echo "  2. Start the orchestrator: adaptive-os start"
    echo "  3. Check status:           adaptive-os status"
    echo "  4. Switch profile:         adaptive-os switch gaming"
    echo "  5. Talk to your OS:        adaptive-os ask 'I want to record a podcast'"
    echo ""
    echo -e "  Docs: ${BLUE}https://github.com/Ivan-IA17/adaptive-os${NC}"
    echo ""
}

# ── Main ──────────────────────────────────────────────────
banner
OS=$(detect_os)
info "Detected OS: $OS"

check_requirements
install_ollama
create_directories
create_default_config

case "$OS" in
    nixos)  warn "NixOS detected. Use 'sudo nixos-rebuild switch --flake $REPO_DIR/nix#work' instead of this script." ;;
    arch)   install_system_deps_arch ;;
    debian) install_system_deps_debian ;;
    *)      warn "Unknown OS. Skipping system package installation." ;;
esac

install_python_package
pull_model
install_systemd_service
symlink_hyprland_config
print_summary
