{
  description = "Lockfile updater";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    treefmt.url = "github:numtide/treefmt-nix";
    treefmt.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    treefmt,
  }: let
    overlay = final: prev: {
      update-lockfile = prev.python3.pkgs.callPackage ./pkg.nix {
        src = self;
      };
    };

    forEachSystem = nixpkgs.lib.genAttrs [
      "aarch64-darwin"
      "aarch64-linux"
      "x86_64-linux"
    ];
    importPkgs = system:
      import nixpkgs {
        inherit system;
        overlays = [overlay];
      };

    treefmtSettings = {
      projectRootFile = "flake.nix";
      programs = {
        alejandra.enable = true;
        prettier.enable = true;
        ruff-format.enable = true;
        taplo.enable = true;
      };
    };
  in {
    overlays = {
      default = overlay;
      update-lockfile = overlay;
    };

    apps = forEachSystem (
      system: let
        pkgs = importPkgs system;
        app = {
          type = "app";
          program = "${pkgs.update-lockfile}/bin/update-lockfile";
        };
      in {
        default = app;
        update-lockfile = app;
      }
    );

    packages = forEachSystem (
      system: let
        pkgs = importPkgs system;
      in {
        default = pkgs.update-lockfile;
        inherit (pkgs) update-lockfile;
      }
    );

    formatter = forEachSystem (
      system: (treefmt.lib.evalModule (importPkgs system) treefmtSettings).config.build.wrapper
    );

    checks = forEachSystem (
      system: let
        pkgs = importPkgs system;
      in {
        inherit (pkgs) update-lockfile;

        formatting = ((treefmt.lib.evalModule pkgs (nixpkgs.lib.recursiveUpdate treefmtSettings
            {
              programs.ruff-check.enable = true;
            }))
          .config
          .build
          .check)
        self;
      }
    );
  };
}
