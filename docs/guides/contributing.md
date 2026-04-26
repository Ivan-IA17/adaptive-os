# Contributing to Adaptive OS

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Code of Conduct

Be respectful, constructive, and inclusive. We welcome contributors of all experience levels.

## Ways to Contribute

- 🐛 **Bug reports** — open a GitHub issue with steps to reproduce
- 💡 **Feature requests** — open a GitHub issue describing the use case
- 📝 **Documentation** — improve or translate docs
- 🧪 **Tests** — add test coverage for untested code paths
- 🎨 **New profiles** — contribute profiles for new activity types
- 🔌 **Detectors** — add new context sensors (browser extension, calendar, etc.)

## Development Setup

```bash
# Clone
git clone https://github.com/Ivan-IA17/adaptive-os
cd adaptive-os

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e "orchestrator/[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check orchestrator/adaptive_os/

# Type check
mypy orchestrator/adaptive_os/
```

## Project Structure

```
adaptive-os/
├── nix/                  # NixOS declarative configuration
│   ├── profiles/         # One .nix file per profile
│   ├── modules/          # Shared NixOS modules
│   └── flake.nix         # Flake entry point
├── orchestrator/         # Python AI daemon
│   └── adaptive_os/
│       ├── core/         # Orchestrator, engine, habits, state
│       ├── detectors/    # Context sensors
│       ├── profiles/     # Profile manager
│       └── api/          # REST API
├── ui/
│   ├── hyprland/         # Compositor configs per profile
│   ├── waybar/           # Status bar configs per profile
│   ├── themes/           # GTK/Qt theme scripts per profile
│   └── rofi/             # App launcher themes
├── scripts/              # install.sh, helper scripts
├── tests/
│   ├── unit/             # Unit tests (no external deps)
│   └── integration/      # Async integration tests
└── docs/
    ├── architecture/     # Design docs
    └── guides/           # User guides
```

## Adding a New Profile

1. **Create the NixOS config** — `nix/profiles/<name>.nix`:
   ```nix
   { config, pkgs, lib, ... }:
   {
     environment.systemPackages = with pkgs; [ ... ];
     powerManagement.cpuFreqGovernor = "performance";
   }
   ```

2. **Create the orchestrator spec** — `orchestrator/profiles/<name>.yaml`:
   ```yaml
   name: myprofile
   display_name: "My Profile"
   icon: "🔧"
   detection:
     apps:
       match_any: [myapp, otherapp]
       weight: 0.8
   ```

3. **Create the Hyprland config** — `ui/hyprland/<name>.conf`

4. **Create the Waybar config** — `ui/waybar/<name>.jsonc`

5. **Create the theme script** — `ui/themes/<name>/apply.sh`

6. **Add to flake.nix** — add `<name> = mkProfile "<name>";` to outputs

7. **Add to KNOWN_PROFILES** in `orchestrator/adaptive_os/core/decision_engine.py`

8. **Write tests** — add detection/switching tests in `tests/`

9. **Update the README** — add the profile to the profiles table

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add voice interface using whisper.cpp
fix: handle ollama connection timeout gracefully
docs: add nixos setup guide
test: add habit tracker unit tests
refactor: extract profile validation logic
chore: update dependencies
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes and write tests
4. Ensure all tests pass: `pytest tests/ -v`
5. Ensure linting passes: `ruff check .`
6. Push and open a PR against `main`
7. Fill in the PR template describing what and why

## Testing Guidelines

- **Unit tests** go in `tests/unit/` — no network calls, no filesystem side effects
- **Integration tests** go in `tests/integration/` — use `tmp_path` for files, mock Ollama
- Use `pytest-asyncio` with `@pytest.mark.asyncio` for async tests
- Aim for 80%+ coverage on new code

## Releasing

Releases follow [Semantic Versioning](https://semver.org/):
- `MAJOR` — breaking changes to the profile spec or API
- `MINOR` — new features (new profiles, new detectors, new API endpoints)
- `PATCH` — bug fixes and documentation

Maintainers tag releases on `main` after merging.
