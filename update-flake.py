import subprocess


def main():
    proc = subprocess.run(
        ["nix", "flake", "update"],
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        encoding="utf-8",
        errors="backslashreplace",
    )
    if proc.returncode != 0:
        print("Failed to run 'nix flake update'")
        exit(proc.returncode)

    msg = "flake.lock: update\n\n"
    for line in proc.stdout.splitlines():
        print(line)
        if not line.lower().startswith("warning"):
            msg += line
            msg += "\n"

    proc = subprocess.run(["git", "add", "flake.lock"])
    if proc.returncode != 0:
        print("Failed to run 'git add flake.lock'")
        exit(proc.returncode)

    proc = subprocess.run(["git", "commit", "-m", msg])
    if proc.returncode != 0:
        print("Failed to run git commit")
        exit(proc.returncode)


if __name__ == "__main__":
    main()
