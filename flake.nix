{
  description = "Lockfile updater";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    overlay = final: prev: {
      update-lockfile =
        prev.writers.writePython3Bin "update-lockfile" {flakeIgnore = ["E501"];}
        (builtins.readFile ./update-lockfile.py);
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

    nixSrc = nixpkgs.lib.sources.sourceFilesBySuffices ./. [".nix"];
    pySrc = nixpkgs.lib.sources.sourceFilesBySuffices ./. [".py"];
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

    checks = forEachSystem (
      system: let
        pkgs = importPkgs system;
      in {
        inherit (pkgs) update-lockfile;

        black = pkgs.runCommand "black" {} ''
          ${pkgs.python3Packages.black}/bin/black ${pySrc}
          touch $out
        '';

        flake8 =
          pkgs.runCommand "flake8"
          {
            buildInputs = with pkgs.python3Packages; [
              flake8
              flake8-bugbear
              pep8-naming
            ];
          }
          ''
            flake8 --max-line-length 88 ${pySrc}
            touch $out
          '';

        alejandra = pkgs.runCommand "alejandra" {} ''
          ${pkgs.alejandra}/bin/alejandra --check ${nixSrc}
          touch $out
        '';

        statix = pkgs.runCommand "statix" {} ''
          ${pkgs.statix}/bin/statix check ${nixSrc}
          touch $out
        '';
      }
    );
  };
}
