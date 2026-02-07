from __future__ import annotations

from pathlib import Path


def ensure_case_dirs(case: str, runs_dir: Path | str = "runs") -> tuple[Path, Path, Path]:
    base = Path(runs_dir) / case
    gmsh = base / "gmsh"
    models = base / "models"

    base.mkdir(parents=True, exist_ok=True)
    gmsh.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)

    return base, gmsh, models


def geometry_parquet(case: str, tag: str = "", runs_dir: Path | str = "runs") -> Path:
    _, gmsh, _ = ensure_case_dirs(case, runs_dir)
    suffix = f"_{tag}" if tag else ""
    return gmsh / f"element_geometry_3d{suffix}.parquet"


def sigma_vm_parquet(case: str, tag: str, runs_dir: Path | str = "runs") -> Path:
    _, gmsh, _ = ensure_case_dirs(case, runs_dir)
    return gmsh / f"sigma_vm_{tag}_3d.parquet"


def dataset_hstar_parquet(case: str, runs_dir: Path | str = "runs") -> Path:
    _, gmsh, _ = ensure_case_dirs(case, runs_dir)
    return gmsh / "dataset_hstar_3d.parquet"


def rf_model_path(case: str, runs_dir: Path | str = "runs") -> Path:
    _, _, models = ensure_case_dirs(case, runs_dir)
    return models / "rf_hstar_3d.joblib"


def h_pred_element_parquet(case: str, runs_dir: Path | str = "runs") -> Path:
    _, gmsh, _ = ensure_case_dirs(case, runs_dir)
    return gmsh / "h_pred_element_3d.parquet"


def h_pred_post_parquet(case: str, runs_dir: Path | str = "runs") -> Path:
    _, gmsh, _ = ensure_case_dirs(case, runs_dir)
    return gmsh / "h_pred_post_3d.parquet"


def background_csv_path(case: str, runs_dir: Path | str = "runs") -> Path:
    _, gmsh, _ = ensure_case_dirs(case, runs_dir)
    return gmsh / "background_points_3d.csv"


def background_pos_path(case: str, runs_dir: Path | str = "runs") -> Path:
    _, gmsh, _ = ensure_case_dirs(case, runs_dir)
    return gmsh / "background_points_3d.pos"