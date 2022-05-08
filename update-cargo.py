import subprocess


def main():
    proc = subprocess.run(
        ["cargo", "update"],
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        encoding="utf-8",
        errors="backslashreplace",
    )
    if proc.returncode != 0:
        print("Failed to run 'cargo update'")
        exit(proc.returncode)

    msg = "Cargo.lock: update\n\n"
    for line in proc.stdout.splitlines():
        print(line)
        prefix = "    Updating "
        if line.startswith(prefix):
            line = line[len(prefix) :]  # noqa: E203
            if line != "crates.io index":
                msg += f"* {line}"
                msg += "\n"

    proc = subprocess.run(["git", "add", "Cargo.lock"])
    if proc.returncode != 0:
        print("Failed to run 'git add Cargo.lock'")
        exit(proc.returncode)

    proc = subprocess.run(["git", "commit", "-m", msg])
    if proc.returncode != 0:
        print("Failed to run git commit")
        exit(proc.returncode)


if __name__ == "__main__":
    main()
