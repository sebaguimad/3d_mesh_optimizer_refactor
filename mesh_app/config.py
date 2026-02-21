# config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunConfig:
    case: str
    geo: Path
    runs_dir: Path = Path("runs")
    gmsh_exe: str = "gmsh"
    python_exe: str = "python"
    sigma_mode: str = "auto"  # auto | dummy | fem
    fem_backend: str = "fallback"  # fallback | calculix
    fem_sigma_coarse_file: Path | None = None
    fem_sigma_ref_file: Path | None = None

    coarse_name: str = "coarse_3d.msh"
    adapt_name: str = "adapt_3d.msh"

    def case_dir(self) -> Path:
        return self.runs_dir / self.case

    def gmsh_dir(self) -> Path:
        return self.case_dir() / "gmsh"

    def models_dir(self) -> Path:
        return self.case_dir() / "models"

    def coarse_msh(self) -> Path:
        return self.gmsh_dir() / self.coarse_name

    def adapt_msh(self) -> Path:
        return self.gmsh_dir() / self.adapt_name

    def background_pos(self) -> Path:
        return self.gmsh_dir() / "background_points_3d.pos"

    def ensure_dirs(self) -> None:
        self.case_dir().mkdir(parents=True, exist_ok=True)
        self.gmsh_dir().mkdir(parents=True, exist_ok=True)
        self.models_dir().mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        if not self.geo.exists():
            raise FileNotFoundError(f"No existe geometría: {self.geo}")
        if self.sigma_mode not in {"auto", "dummy", "fem"}:
            raise ValueError("sigma_mode debe ser 'auto', 'dummy' o 'fem'")
        if self.fem_backend not in {"fallback", "calculix"}:
            raise ValueError("fem_backend debe ser 'fallback' o 'calculix'")
