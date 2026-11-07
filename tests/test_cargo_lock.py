import os

from update_lockfile import cargo_update_msg, read_cargo_git_revs

this_dir = os.path.dirname(os.path.abspath(__file__))


def test_read_cargo_git_revs():
    path = os.path.join(this_dir, "Cargo.lock.a.toml")
    expected = {
        "https://github.com/newam/jsonwebtoken.git": {
            "c5bb9a7c71f304371596dbb2454dc7c2e103371d"
        },
        "file:///home/user/mydep": {"a063e8ff9add3b01bfca5519a266b66166a8afcf"},
    }
    assert read_cargo_git_revs(path) == expected


def test_cargo_update_msg():
    a = read_cargo_git_revs(os.path.join(this_dir, "Cargo.lock.a.toml"))
    b = read_cargo_git_revs(os.path.join(this_dir, "Cargo.lock.b.toml"))
    lines = [
        "    Updating git repository `https://github.com/newam/jsonwebtoken.git`",
        "    Updating git repository `file:///home/user/mydep`",
        "    Updating git repository `https://github.com/user/newdep.git`",
        "    Updating crates.io index",
        "     Locking 2 packages to highest compatible versions",
        "    Updating mydep v0.1.0 (file:///home/user/mydep#a063e8ff) -> #8d23198c",
        "    Updating serde v1.0.210 -> v1.0.211",
        "note: pass `--verbose` to see 1 unchanged dependencies behind latest",
    ]
    expected = [
        # unchanged git repositories are omitted
        "updated git repository `file:///home/user/mydep`",
        # new git repositories are kept
        "updated git repository `https://github.com/user/newdep.git`",
        "updated mydep v0.1.0 (file:///home/user/mydep#a063e8ff) -> #8d23198c",
        "updated serde v1.0.210 -> v1.0.211",
    ]
    assert cargo_update_msg(lines, a, b) == expected
