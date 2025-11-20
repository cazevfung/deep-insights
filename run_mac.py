"""Compatibility shim for macOS/Linux launcher."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).parent
    target = repo_root / "scripts" / "install" / "run_mac.py"

    if not target.exists():
        sys.stderr.write(
            "Error: scripts/install/run_mac.py was not found. "
            "Please ensure the repository is complete.\n"
        )
        sys.exit(1)

    print("Note: macOS/Linux launcher moved to scripts/install/run_mac.py")
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()

