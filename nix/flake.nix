{
  description = "Adaptive OS — AI-driven NixOS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager/release-24.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    hyprland.url = "github:hyprwm/Hyprland";
  };

  outputs = { self, nixpkgs, nixpkgs-unstable, home-manager, hyprland, ... }@inputs:
  let
    system = "x86_64-linux";

    overlay = import ./overlays/adaptive-os.nix { inherit inputs; };

    pkgs = import nixpkgs {
      inherit system;
      overlays = [ overlay ];
    };

    # Build a complete NixOS system for a given profile
    mkProfile = profileName: nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [
        ./modules/base.nix
        ./modules/ai-orchestrator.nix
        ./modules/wayland.nix
        ./profiles/${profileName}.nix
        home-manager.nixosModules.home-manager
        { nixpkgs.overlays = [ overlay ]; }
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
        }
      ];
      specialArgs = { inherit inputs profileName; };
    };
  in
  {
    # Overlay — lets downstream flakes consume adaptive-os as a package
    overlays.default = overlay;

    # Installable package: nix run github:Ivan-IA17/adaptive-os
    packages.${system} = {
      adaptive-os = pkgs.adaptive-os;
      default     = pkgs.adaptive-os;
    };

    nixosConfigurations = {
      work     = mkProfile "work";
      gaming   = mkProfile "gaming";
      creative = mkProfile "creative";
      server   = mkProfile "server";
      study    = mkProfile "study";
    };

    # Expose profiles for the orchestrator to build
    profiles = {
      work     = self.nixosConfigurations.work.config.system.build.toplevel;
      gaming   = self.nixosConfigurations.gaming.config.system.build.toplevel;
      creative = self.nixosConfigurations.creative.config.system.build.toplevel;
      server   = self.nixosConfigurations.server.config.system.build.toplevel;
      study    = self.nixosConfigurations.study.config.system.build.toplevel;
    };

    # Dev shell: nix develop
    devShells.${system}.default = pkgs.mkShell {
      packages = with pkgs; [
        python3
        python3Packages.pip
        python3Packages.pytest
        python3Packages.pytest-asyncio
        ruff
        mypy
        ollama
      ];
      shellHook = ''
        pip install -e orchestrator/ --quiet
        echo "Adaptive OS dev shell ready. Run: pytest tests/ -v"
      '';
    };
  };
}
