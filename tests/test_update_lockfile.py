import sys
import os

this_dir = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.abspath(os.path.join(this_dir, ".."))

if top_dir not in sys.path:
    sys.path.append(top_dir)

from update_lockfile import read_poetry_lock, PoetryPackage  # noqa: E402


def test_read_poetry_lock():
    poetry_lock = read_poetry_lock(os.path.join(this_dir, "poetry.lock.toml"))
    assert poetry_lock == [PoetryPackage(name="alabaster", version="0.7.12")]
