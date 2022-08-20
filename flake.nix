{
  description = "Lockfile updaters";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable-small";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [
      "aarch64-darwin"
      "aarch64-linux"
      "x86_64-linux"
    ]
      (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        rec {
          packages.default = pkgs.writers.writePython3Bin "update-lockfile" { }
            (builtins.readFile ./update-lockfile.py);

          apps.default = {
            type = "app";
            program = "${packages.default}/bin/update-lockfile";
          };

          checks = {
            pkg = packages.default;

            black = pkgs.runCommand "black" { } ''
              ${pkgs.python3Packages.black}/bin/black ${./.}
              touch $out
            '';

            flake8 = pkgs.runCommand "flake8"
              {
                buildInputs = with pkgs.python3Packages; [
                  flake8
                  flake8-bugbear
                  pep8-naming
                ];
              }
              ''
                flake8 --max-line-length 88 ${./.}
                touch $out
              '';

            nixpkgs-fmt = pkgs.runCommand "nixpkgs-fmt" { } ''
              ${pkgs.nixpkgs-fmt}/bin/nixpkgs-fmt --check ${./.}
              touch $out
            '';

            statix = pkgs.runCommand "statix" { } ''
              ${pkgs.statix}/bin/statix check ${./.}
              touch $out
            '';
          };
        }
      );
}
