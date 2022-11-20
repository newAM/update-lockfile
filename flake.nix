{
  description = "Lockfile updater";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    src = builtins.path {
      path = ./.;
      name = "update-lockfile";
    };

    overlay = final: prev: {
      update-lockfile =
        (prev.writers.makeScriptWriter {interpreter = "${prev.python311}/bin/python";}) "/bin/update-lockfile"
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
      system: let
        pkgs = importPkgs system;
      in
        pkgs.alejandra
    );

    checks = let
      nixSrc = nixpkgs.lib.sources.sourceFilesBySuffices src [".nix"];
      pySrc = nixpkgs.lib.sources.sourceFilesBySuffices src [".py" ".toml"];
    in
      forEachSystem (
        system: let
          pkgs = importPkgs system;
        in {
          inherit (pkgs) update-lockfile;

          pytest = pkgs.runCommand "pytest" {} ''
            ${pkgs.python311Packages.pytest}/bin/pytest ${pySrc}
            touch $out
          '';

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
