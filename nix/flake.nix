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
    pkgs = nixpkgs.legacyPackages.${system};

    # Build a complete NixOS system for a given profile
    mkProfile = profileName: nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [
        ./modules/base.nix
        ./modules/ai-orchestrator.nix
        ./modules/wayland.nix
        ./profiles/${profileName}.nix
        home-manager.nixosModules.home-manager
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
        }
      ];
      specialArgs = { inherit inputs profileName; };
    };
  in
  {
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
  };
}
