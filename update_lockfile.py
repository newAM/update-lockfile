import argparse
import asyncio
import os
import tomllib
from typing import List, NamedTuple, Optional


class LockfileUpdate(NamedTuple):
    lockfile: str
    lines: List[str]


class SubprocessError(Exception):
    def __init__(self, message: str, returncode: Optional[int]):
        super().__init__(message)
        self.returncode = returncode


class PoetryPackage(NamedTuple):
    name: str
    version: str


def read_poetry_lock(path: str) -> List[PoetryPackage]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    ret = []
    for pkg in data["package"]:
        ret.append(PoetryPackage(name=pkg["name"], version=pkg["version"]))
    return ret


def poetry_lock_diff(a: List[PoetryPackage], b: List[PoetryPackage]) -> List[str]:
    ret = []

    found = []
    for pa in a:
        for pb in b:
            if pa.name == pb.name:
                if pa.version != pb.version:
                    ret.append(f"updated {pa.name} {pa.version} -> {pb.version}")
                found.append(pa.name)
                break

        if pa.name not in found:
            ret.append(f"removed {pa.name} {pa.version}")
            found.append(pa.name)

        for pb in b:
            if pb.name not in found:
                ret.append(f"added {pa.name} {pa.version}")
                found.append(pb.name)

    return ret


async def run(cmd: List[str]) -> List[str]:
    cmds = " ".join(cmd)
    print(f"Running `{cmds}`")
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.STDOUT,
        stdout=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        msg = f"Failed with {proc.returncode} running `{cmds}`"
        print(msg)
        raise SubprocessError(msg, proc.returncode)
    lines = []
    for line in stdout.decode("utf-8").splitlines():
        if line:
            lines.append(line)
    return lines


async def git_add(file: str):
    return await run(["git", "add", file])


async def is_dirty(file: str) -> bool:
    try:
        await run(["git", "diff", "-s", "--exit-code", file])
        return False
    except SubprocessError:
        return True


async def update_cargo() -> Optional[LockfileUpdate]:
    lockfile = "Cargo.lock"
    lines = await run(["cargo", "update"])
    if not await is_dirty(lockfile):
        return None
    await git_add(lockfile)

    msg = []
    for line in lines:
        line = line.strip().lower()
        if line == "updating crates.io index":
            continue
        if line.lower().startswith("note:"):
            continue

        words = line.split()
        verb = words[0]

        if verb.endswith("ing"):
            verb = verb[:-3]
            verb += "ed"

        msg.append(f"{verb} " + " ".join(words[1:]))

    return LockfileUpdate(lockfile, msg)


async def update_flake() -> Optional[LockfileUpdate]:
    lockfile = "flake.lock"
    lines = await run(["nix", "flake", "update"])
    if not await is_dirty(lockfile):
        return None
    await git_add(lockfile)

    msg = []
    for line in lines:
        if line.startswith(("• ", "  ")):
            msg.append(line)
    return LockfileUpdate(lockfile, msg)


async def update_poetry() -> Optional[LockfileUpdate]:
    lockfile = "poetry.lock"
    a = read_poetry_lock(lockfile)
    await run(["poetry", "update", "--no-interaction", "--no-ansi", "--lock"])
    if not await is_dirty(lockfile):
        return None
    b = read_poetry_lock(lockfile)
    await git_add(lockfile)

    # poetry does not display updated deps, diff manually
    msg = poetry_lock_diff(a, b)

    return LockfileUpdate(lockfile, msg)


async def amain(args: argparse.Namespace) -> Optional[int]:
    print("Autodetecting lockfiles from current directory")

    coros = []
    for file in os.listdir():
        if file == "Cargo.lock":
            if "cargo" in args.skip:
                print("Skipping Cargo.lock")
            else:
                coros.append(update_cargo())
        elif file == "flake.lock":
            if "flake" in args.skip:
                print("Skipping flake.lock")
            else:
                coros.append(update_flake())
        elif file == "poetry.lock":
            if "poetry" in args.skip:
                print("Skipping poetry.lock")
            else:
                coros.append(update_poetry())

    if len(coros) == 0:
        print("No lockfiles to update")
        return 1

    try:
        updates = await asyncio.gather(*coros)
    except SubprocessError as e:
        return e.returncode

    updates = [u for u in updates if u is not None]

    if len(updates) == 0:
        print("Everything is already up-to-date!")
        return 0

    msg = ", ".join([u.lockfile for u in updates])
    msg += ": update\n\n"
    for idx, update in enumerate(updates):
        msg += "\n".join(update.lines)

        # create a space between messages if not the last file
        if idx != len(updates) - 1:
            msg += "\n\n"

    if not args.no_commit:
        await run(["git", "commit", "-m", msg])
    else:
        print(msg)

    return 0


def main():
    parser = argparse.ArgumentParser(description="Update lockfiles")
    parser.add_argument(
        "-n",
        "--no-commit",
        action="store_true",
        help="Update lockfiles without a commit",
    )
    parser.add_argument(
        "-s",
        "--skip",
        choices=["poetry", "cargo", "flake"],
        action="append",
        default=[],
        help="Skip updating this type of lockfile",
    )
    args = parser.parse_args()

    rc = asyncio.run(amain(args))
    exit(rc)


if __name__ == "__main__":
    main()
