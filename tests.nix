{
  buildPythonPackage,
  update-lockfile,
  pytestCheckHook,
}:
buildPythonPackage {
  pname = "${update-lockfile.pname}-tests";
  inherit (update-lockfile) version src dependencies;
  format = "other";

  dontBuild = true;
  dontInstall = true;

  nativeCheckInputs = [
    pytestCheckHook
    update-lockfile
  ];
}
