{
  lib,
  buildPythonApplication,
  src,
  setuptools,
  rich,
  pytestCheckHook,
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

    nativeCheckInputs = [
      pytestCheckHook
    ];

    meta = {
      description = pyprojectToml.project.description;
      homepage = pyprojectToml.project.urls.Repository;
      changelog = pyprojectToml.project.urls.Changelog;
      license = lib.licenses.mit;
      maintainers = [lib.maintainers.newam];
    };
  }
