# SPDX-License-Identifier: MIT
"""Sync the existing locked environment without removing or replacing it."""
from pathlib import Path
import subprocess
import argparse


def check(project, *, allow_missing=False):
    project = Path(project).resolve()
    env = project / ".venv"
    if env.is_symlink():
        raise ValueError("environment link")
    if not env.exists() and not allow_missing:
        raise ValueError("missing environment")
    if env.exists():
        config = env / "pyvenv.cfg"
        if not (env / "bin/python").is_file() or not config.is_file():
            raise ValueError("incomplete environment")
        lines = dict(line.split(" = ", 1) for line in config.read_text().splitlines() if " = " in line)
        if not lines.get("version", lines.get("version_info", "")).startswith("3.12."):
            raise ValueError("different Python version")


def ensure(project, runner=None):
    runner = subprocess.run if runner is None else runner
    project = Path(project).resolve()
    check(project, allow_missing=True)
    runner(["uv", "sync", "--locked", "--python", "3.12", "--project", str(project)], check=True)
    print("Locked Premier environment is ready. Repeating make setup reuses .venv; vendor inputs and transfer state are preserved.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Inspect existing environment without sync or creation')
    args = parser.parse_args()
    try:
        project = Path(__file__).resolve().parent
        if args.check:
            check(project)
        else:
            ensure(project)
        return 0
    except ValueError:
        print("Environment not ready (ValueError). Run make setup if .venv is missing. If it is incomplete, linked or uses a different Python version, preserve this folder and open a fresh README-button Codespace. Nothing was replaced.")
    except (OSError, subprocess.CalledProcessError) as error:
        kind = "CalledProcessError" if isinstance(error, subprocess.CalledProcessError) else "OSError"
        print("Setup stopped (" + kind + "). Check the installation output and network, then run make setup again. No vendor file or transfer journal was reset.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
