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
      update-lockfile =
        (prev.writers.makeScriptWriter {interpreter = "${prev.python3}/bin/python";}) "/bin/update-lockfile"
        (builtins.readFile ./update_lockfile.py);
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

    treefmtEval = system:
      treefmt.lib.evalModule (importPkgs system) {
        projectRootFile = "flake.nix";
        programs = {
          alejandra.enable = true;
          prettier.enable = true;
          ruff.enable = true;
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
      system: (treefmtEval system).config.build.wrapper
    );

    checks = let
      nixSrc = nixpkgs.lib.sources.sourceFilesBySuffices self [".nix"];
      pySrc = nixpkgs.lib.sources.sourceFilesBySuffices self [".py" ".toml"];
    in
      forEachSystem (
        system: let
          pkgs = importPkgs system;
        in {
          inherit (pkgs) update-lockfile;

          pytest = pkgs.runCommand "pytest" {} ''
            ${pkgs.python3Packages.pytest}/bin/pytest ${pySrc}
            touch $out
          '';

          formatting = (treefmtEval system).config.build.check self;

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

          statix = pkgs.runCommand "statix" {} ''
            ${pkgs.statix}/bin/statix check ${nixSrc}
            touch $out
          '';
        }
      );
  };
}
