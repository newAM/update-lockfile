import os
from update_lockfile import read_poetry_lock, PoetryPackage

this_dir = os.path.dirname(os.path.abspath(__file__))


def test_read_poetry_lock():
    poetry_lock = read_poetry_lock(os.path.join(this_dir, "poetry.lock.toml"))
    assert poetry_lock == [PoetryPackage(name="alabaster", version="0.7.12")]
