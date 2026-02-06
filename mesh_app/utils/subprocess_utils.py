# subprocess_utils.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


def _pretty(cmd: Iterable[str]) -> str:
    return " ".join([f'"{c}"' if " " in c else c for c in cmd])


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    printable = _pretty(cmd)
    print(f"\n[cmd] {printable}")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if proc.returncode != 0:
        raise RuntimeError(f"Comando falló ({proc.returncode}): {printable}")