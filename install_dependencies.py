"""Compatibility shim for the relocated installer script."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).parent
    target = repo_root / "scripts" / "install" / "install_dependencies.py"

    if not target.exists():
        sys.stderr.write(
            "Error: scripts/install/install_dependencies.py was not found. "
            "Please verify that the repository is intact.\n"
        )
        sys.exit(1)

    print("Note: installer moved to scripts/install/install_dependencies.py")
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()

