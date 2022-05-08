{
  description = "Lockfile updaters";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [
      "x86_64-linux"
      "aarch64-linux"
      "aarch64-darwin"
    ]
      (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        rec {
          packages = {
            update-cargo = pkgs.writers.writePython3Bin "update-cargo" { }
              (builtins.readFile ./update-cargo.py);
            update-flake = pkgs.writers.writePython3Bin "update-flake" { }
              (builtins.readFile ./update-flake.py);
          };
          apps = {
            update-cargo = flake-utils.lib.mkApp { drv = packages.update-cargo; };
            update-flake = flake-utils.lib.mkApp { drv = packages.update-flake; };
          };

          checks = {
            format = pkgs.runCommand "format" { } ''
              ${pkgs.nixpkgs-fmt}/bin/nixpkgs-fmt --check ${./.}
              ${pkgs.python3Packages.black}/bin/black ${./.}
              touch $out
            '';

            lint = pkgs.runCommand "lint" { } ''
              ${pkgs.statix}/bin/statix check ${./.}
              ${pkgs.python3Packages.flake8}/bin/flake8 ${./.}
              touch $out
            '';
          };
        }
      );
}
