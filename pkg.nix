{
  lib,
  buildPythonApplication,
  src,
  setuptools,
  rich,
  callPackage,
}: let
  pyprojectToml = lib.importTOML ./pyproject.toml;
in
  buildPythonApplication {
    pname = pyprojectToml.project.name;
    version = pyprojectToml.project.version;
    pyproject = true;

    inherit src;

    build-system = [
      setuptools
    ];

    dependencies = [
      rich
    ];

    # tests are in passthru.tests for end-to-end CLI testing
    doCheck = false;

    passthru.tests = {
      tests = callPackage ./tests.nix {};
    };

    meta = {
      description = pyprojectToml.project.description;
      homepage = pyprojectToml.project.urls.Repository;
      changelog = pyprojectToml.project.urls.Changelog;
      license = lib.licenses.mit;
      maintainers = [lib.maintainers.newam];
    };
  }
