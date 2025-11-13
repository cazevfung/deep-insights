#!/usr/bin/env python3
"""
Research Tool - Dependency Installer (macOS/Linux) - Python version.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
PORTS: List[int] = [3000, 3001]


def print_divider(title: str | None = None) -> None:
  line = "=" * 60
  print(line)
  if title:
    print(title)
    print(line)
  else:
    print(line)


def ensure_python_version() -> None:
  if sys.version_info < (3, 9):
    print("Python 3.9+ not found!")
    print("Please install Python 3.9 or newer from https://www.python.org/downloads/")
    print("Ensure the interpreter is available as 'python3' (recommended) or 'python'.")
    sys.exit(1)

  print(f"Python found: {sys.executable}")
  subprocess.run([sys.executable, "--version"], check=False)
  print()
  print("Testing Python execution...")
  try:
    subprocess.run(
        [sys.executable, "-c", "import sys; print('Python path:', sys.executable)"],
        check=True,
    )
  except subprocess.CalledProcessError:
    print("Python test failed!")
    sys.exit(1)
  print("Python test passed!")
  print()


def run_lsof(port: int) -> List[int]:
  try:
    result = subprocess.run(
        ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTENING"],
        check=False,
        capture_output=True,
        text=True,
    )
  except FileNotFoundError:
    print("Warning: 'lsof' command not found; cannot inspect ports automatically.")
    return []

  if result.returncode != 0 or not result.stdout.strip():
    return []

  pids: List[int] = []
  for line in result.stdout.strip().splitlines():
    line = line.strip()
    if line:
      try:
        pids.append(int(line))
      except ValueError:
        continue
  return pids


def kill_pids(pids: Iterable[int], sig: signal.Signals) -> None:
  for pid in pids:
    try:
      print(f"    Sending {sig.name} to PID {pid}")
      os.kill(pid, sig.value)
    except ProcessLookupError:
      pass
    except Exception as exc:  # pragma: no cover - defensive logging
      print(f"    Warning: unable to kill PID {pid}: {exc}")


def free_ports(ports: Iterable[int]) -> None:
  print()
  print_divider("Force quitting all server processes...")
  print()

  for port in ports:
    print(f"Checking port {port}...")
    pids = run_lsof(port)
    if not pids:
      continue

    print(f"  Gracefully stopping processes on port {port}: {', '.join(map(str, pids))}")
    kill_pids(pids, signal.SIGTERM)

    time.sleep(1)
    remaining = run_lsof(port)
    if remaining:
      print(f"  Forcing kill on port {port}: {', '.join(map(str, remaining))}")
      kill_pids(remaining, signal.SIGKILL)

  time.sleep(2)

  print("Verifying ports are free...")
  ports_in_use = [port for port in ports if run_lsof(port)]
  if ports_in_use:
    print(f"Warning: Ports {' '.join(map(str, ports_in_use))} may still be in use.")
    print("If you encounter port conflicts, manually kill the processes or restart your computer.")
  else:
    print("All server ports are free.")
  print()
  print_divider()
  print()


def parse_args(argv: List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument("--start", action="store_true")
  parser.add_argument("--no-start", dest="no_start", action="store_true")
  known, unknown = parser.parse_known_args(argv)
  setattr(known, "unknown", unknown)
  return known


def build_extra_args(args: argparse.Namespace, raw_args: List[str]) -> List[str]:
  extra_args = list(raw_args)
  has_start_arg = args.start or args.no_start
  start_server = args.start or not args.no_start

  if start_server and not has_start_arg:
    extra_args.append("--start")
  return extra_args


def run_install_dependencies(extra_args: List[str]) -> None:
  install_script = SCRIPT_DIR / "install_dependencies.py"
  if not install_script.exists():
    print(f"Error: {install_script} not found.")
    sys.exit(1)

  print("Starting dependency installation...")
  print()

  completed = subprocess.run(
      [sys.executable, str(install_script), *extra_args],
      check=False,
  )

  if completed.returncode != 0:
    print()
    print("Installation completed with errors.")
    print(f"Exit code: {completed.returncode}")
    print()
    sys.exit(completed.returncode)

  print()
  print("Installation completed successfully!")
  print()


def main(argv: List[str]) -> None:
  print_divider("Research Tool - Dependency Installer (macOS/Linux)")
  print()

  ensure_python_version()
  free_ports(PORTS)

  parsed = parse_args(argv)
  extra_args = build_extra_args(parsed, argv)
  run_install_dependencies(extra_args)


if __name__ == "__main__":
  main(sys.argv[1:])

