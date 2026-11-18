"""Fail closed before publishing any tracked snapshot or outgoing identity."""

import subprocess
import sys

PRIVATE = ["-e", "dgold" + "267", "-e", "gmail" + ".com"]
ALLOWED = {
    "144842775+davidgold00@users.noreply.github.com",
    "41898282+github-actions[bot]@users.noreply.github.com",
}


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def check_tree(*refs):
    result = subprocess.run(["git", "grep", "-q", "-i", *PRIVATE, *refs], check=False)
    if result.returncode != 1:
        raise SystemExit(
            "Private contact found or tracked tree could not be scanned. Push stopped."
        )


def main():
    check_tree()
    branch = git("branch", "--show-current")
    if not branch:
        raise SystemExit("Select the branch being pushed.")
    remote = "refs/remotes/origin/" + branch
    exists = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", remote], check=False
    ).returncode
    revisions = [f"{remote}..HEAD"] if exists == 0 else ["HEAD", "--not", "--remotes=origin"]
    commits = git("rev-list", *revisions).splitlines()
    for sha in commits:
        check_tree(sha)
        if not set(git("show", "-s", "--format=%ae%n%ce", sha).splitlines()) <= ALLOWED:
            raise SystemExit("Private or unexpected outgoing commit identity. Push stopped.")
        message = git("show", "-s", "--format=%B", sha).lower()
        if any(token in message for token in PRIVATE[1::2]):
            raise SystemExit("Private contact in commit message. Push stopped.")
    print(f"Privacy checks passed for tracked files and {len(commits)} outgoing commits.")


if __name__ == "__main__":
    sys.exit(main())
