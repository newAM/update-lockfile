import argparse
import asyncio
import os
import tomllib
from typing import List, NamedTuple, Optional, Callable, Any
from rich.progress import Progress, SpinnerColumn, TextColumn
from dataclasses import dataclass


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
            ret.append(f"added {pb.name} {pb.version}")
            found.append(pb.name)

    return ret


async def run(cmd: List[str]) -> List[str]:
    cmds = " ".join(cmd)
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
    proc = await asyncio.create_subprocess_exec(
        "git", "diff", "-s", "--exit-code", file
    )
    await proc.communicate()
    return proc.returncode == 1


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
        if line.lower().startswith("locking "):
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


class Lockfile(NamedTuple):
    file_name: str
    function: Callable
    emoji: str
    skip_flag: str

    def description(self) -> str:
        return f"{self.emoji} Updating {self.file_name}..."

    def description_updated(self) -> str:
        return f"{self.emoji} Updated {self.file_name}"

    def description_no_update(self) -> str:
        return f"{self.emoji} {self.file_name} is up-to-date!"

    def description_error(self) -> str:
        return f"{self.emoji} Failed to update {self.file_name}"


lockfiles = [
    Lockfile(
        file_name="Cargo.lock",
        function=update_cargo,
        emoji="🦀",
        skip_flag="cargo",
    ),
    Lockfile(
        file_name="flake.lock",
        function=update_flake,
        emoji="❄️",
        skip_flag="flake",
    ),
    Lockfile(
        file_name="poetry.lock",
        function=update_poetry,
        emoji="📖",
        skip_flag="poetry",
    ),
]


@dataclass
class UpdateTask:
    task: asyncio.Task
    task_id: Any
    lockfile: Lockfile
    result: Optional[LockfileUpdate] = None


async def amain(args: argparse.Namespace) -> Optional[int]:
    updates = []
    for file in os.listdir():
        for lockfile in lockfiles:
            if file == lockfile.file_name:
                if lockfile in args.skip:
                    print(f"Skipping {lockfile.file_name}")
                else:
                    updates.append(lockfile)

    num_updates: int = len(updates)

    if num_updates == 0:
        print("No lockfiles to update")
        return 0

    with Progress(
        SpinnerColumn(finished_text="✅"),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        update_tasks = []
        for update in updates:
            update_tasks.append(
                UpdateTask(
                    task=asyncio.create_task(update.function()),
                    task_id=progress.add_task(update.description(), total=1),
                    lockfile=update,
                )
            )

        completions: List[str] = []
        while True:
            for update_task in update_tasks:
                if update_task.task.done():
                    if update_task.lockfile.file_name in completions:
                        continue
                    completions.append(update_task.lockfile.file_name)
                    try:
                        update_task.result = update_task.task.result()
                    except Exception as e:
                        print(e)
                        progress.update(
                            update_task.task_id,
                            description=update_task.lockfile.description_error(),
                        )
                    else:
                        if update_task.result is None:
                            description = update_task.lockfile.description_no_update()
                        else:
                            description = update_task.lockfile.description_updated()
                        progress.update(
                            update_task.task_id,
                            description=description,
                            completed=1,
                        )
                else:
                    progress.update(update_task.task_id)

            if len(completions) == num_updates:
                break
            else:
                await asyncio.sleep(0.02)

    results = [u.result for u in update_tasks if u.result is not None]

    if len(results) == 0:
        return 0

    msg = ", ".join([r.lockfile for r in results])
    msg += ": update\n\n"
    for idx, update in enumerate(results):
        msg += "\n".join(update.lines)

        # create a space between messages if not the last file
        if idx != len(results) - 1:
            msg += "\n\n"

    if not args.no_commit:
        await run(["git", "commit", "-m", msg])

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
