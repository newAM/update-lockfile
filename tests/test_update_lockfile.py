import os
from update_lockfile import read_poetry_lock, PoetryPackage, poetry_lock_diff

this_dir = os.path.dirname(os.path.abspath(__file__))


def test_read_poetry_lock():
    poetry_lock = read_poetry_lock(os.path.join(this_dir, "poetry.lock.toml"))
    assert poetry_lock == [PoetryPackage(name="alabaster", version="0.7.12")]


def test_poetry_diff():
    a = read_poetry_lock(os.path.join(this_dir, "poetry.lock.a.toml"))
    b = read_poetry_lock(os.path.join(this_dir, "poetry.lock.b.toml"))
    expected = [
        "updated babel 2.13.0 -> 2.13.1",
        "updated charset-normalizer 3.3.0 -> 3.3.2",
        "updated platformdirs 3.11.0 -> 4.0.0",
        "updated pytest-asyncio 0.22.0 -> 0.21.1",
        "updated urllib3 2.0.7 -> 2.1.0",
        "added setuptools 68.2.2",
    ]
    assert poetry_lock_diff(a, b) == expected
