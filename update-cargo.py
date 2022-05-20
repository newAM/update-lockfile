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
        line = line.strip().lower()
        if line == "updating crates.io index":
            continue

        words = line.split()
        verb = words[0]

        if verb.endswith("ing"):
            verb = verb[:-3]
            verb += "ed"

        msg += f"{verb} "
        msg += " ".join(words[1:])
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
