from __future__ import annotations

from pathlib import Path


def default_sigma_file(case: str, runs_dir: str | Path, tag: str) -> Path:
    """
    Ruta por defecto esperada para resultados exportados desde FEniCS.

    Convención:
      runs/<case>/gmsh/fenics_sigma_vm_<tag>.csv
    """
    return Path(runs_dir) / case / "gmsh" / f"fenics_sigma_vm_{tag}.csv"
