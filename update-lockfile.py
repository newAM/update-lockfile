import argparse
import asyncio
import os
from typing import List, NamedTuple, Optional


class LockfileUpdate(NamedTuple):
    lockfile: str
    lines: List[str]


class SubprocessError(Exception):
    def __init__(self, message: str, returncode: int):
        super().__init__(message)
        self.returncode = returncode


async def run(cmd: List[str]) -> List[str]:
    cmds = " ".join(cmd)
    print(f"Running `{cmds}`")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.STDOUT,
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        msg = f"Failed with {proc.returncode} running `{cmds}`"
        print(msg)
        raise SubprocessError(msg, proc.returncode)
    lines = []
    for line in stdout.decode("utf-8").splitlines():
        print(line)
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


async def update_flake() -> Optional[LockfileUpdate]:
    lockfile = "flake.lock"
    lines = await run(["nix", "flake", "update"])
    if not await is_dirty(lockfile):
        return None
    await git_add(lockfile)

    msg = []
    for line in lines:
        if not line.lower().startswith("warning"):
            msg.append(line)
    return LockfileUpdate(lockfile, msg)


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

        words = line.split()
        verb = words[0]

        if verb.endswith("ing"):
            verb = verb[:-3]
            verb += "ed"

        msg.append(f"{verb} " + " ".join(words[1:]))

    return LockfileUpdate(lockfile, msg)


async def amain(args: argparse.Namespace) -> int:
    print("Autodetecting lockfiles from current directory")

    coros = []
    for file in os.listdir():
        if file == "Cargo.lock":
            coros.append(update_cargo())
        elif file == "flake.lock":
            coros.append(update_flake())

    if len(coros) == 0:
        print("No lockfiles to update")
        return 1

    try:
        updates = await asyncio.gather(*coros)
    except SubprocessError as e:
        return e.returncode

    updates = [u for u in updates if u is not None]

    msg = []
    subject = "; ".join([u.lockfile for u in updates])
    subject += ": update\n"
    msg.append(subject)
    for idx, update in enumerate(updates):
        msg.extend(update.lines)

        # create a space between messages if not the last file
        if idx != len(updates) - 1:
            msg.append("")

    await run(["git", "commit", "-m", "\n".join(msg)])

    return 0


def main():
    parser = argparse.ArgumentParser(description="Update lockfiles")
    args = parser.parse_args()

    rc = asyncio.run(amain(args))
    exit(rc)


if __name__ == "__main__":
    main()
