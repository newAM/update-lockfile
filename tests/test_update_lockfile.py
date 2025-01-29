import tempfile
import subprocess


def test_no_lockfiles():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = subprocess.check_output(["update-lockfile"], cwd=tmpdir, encoding="utf-8")
        assert out == "No lockfiles to update\n"
