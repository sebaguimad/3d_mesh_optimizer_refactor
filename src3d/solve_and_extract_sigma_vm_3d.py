# src3d/solve_and_extract_sigma_vm_3d.py
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src3d.fem.parse_results import read_sigma_vm_table
from src3d.fem.calculix_runner import run_ccx
from src3d.paths3d import ensure_case_dirs, geometry_parquet, sigma_vm_parquet


def _normalize_cli_path(path: Path | str) -> Path:
    clean = str(path).strip().strip('"').strip("'")
    return Path(clean).expanduser()


def _fallback_sigma(
    geom: pd.DataFrame,
    tag: str,
    tipx: float,
    tipy: float,
    tipz: float,
    sigma0: float,
    amp: float,
    r0: float,
) -> pd.DataFrame:
    """
    Fallback gaussiano:
    genera un "hotspot" de tensión alrededor del punto (tipx,tipy,tipz).
    Sirve para probar el pipeline sin solver FEM real.
    """
    tip = np.array([tipx, tipy, tipz], dtype=float)
    c = geom[["cx", "cy", "cz"]].values.astype(float)
    r = np.linalg.norm(c - tip[None, :], axis=1)

    if tag == "coarse":
        sigma = sigma0 + amp * np.exp(-(r / r0) ** 2)
    else:
        sigma = sigma0 + 0.6 * amp * np.exp(-(r / (1.4 * r0)) ** 2)

    return pd.DataFrame(
        {"elem_id": geom["elem_id"].astype(int), "sigma_vm": sigma.astype(float)}
    )


def _default_ccx_workdir(case: str, runs_dir: str | Path, tag: str) -> Path:
    # runs/<case>/ccx/<tag>/
    return Path(runs_dir) / case / "ccx" / tag


def _default_sigma_csv(case: str, runs_dir: str | Path, tag: str) -> Path:
    # runs/<case>/ccx/<tag>/sigma_vm.csv
    return _default_ccx_workdir(case, runs_dir, tag) / "sigma_vm.csv"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Genera sigma_vm por elemento para tag coarse/ref (fallback o CalculiX)."
    )
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--tag", required=True, choices=["coarse", "ref"])
    ap.add_argument("--geom-tag", default="", help="tag de geometría: '' o 'adapt'")

    ap.add_argument("--backend", choices=["fallback", "calculix"], default="fallback")

    # Entrada genérica para calculix: CSV/Parquet con elem_id,sigma_vm
    ap.add_argument(
        "--sigma-file",
        default="",
        help="(calculix) Archivo elem_id,sigma_vm (.csv/.parquet). "
             "Si no se da: runs/<case>/ccx/<tag>/sigma_vm.csv",
    )

    # Fallback params
    ap.add_argument("--tipx", type=float, default=0.25)
    ap.add_argument("--tipy", type=float, default=0.50)
    ap.add_argument("--tipz", type=float, default=0.005)
    ap.add_argument("--sigma0", type=float, default=100.0)
    ap.add_argument("--amp", type=float, default=80.0)
    ap.add_argument("--r0", type=float, default=0.08)

    # CalculiX params
    ap.add_argument("--ccx-exe", default="ccx")
    ap.add_argument("--ccx-job", default="job", help="Nombre del job (sin extensión), ej: job -> job.inp")
    ap.add_argument("--ccx-workdir", default="", help="Workdir de ccx. Si no se da: runs/<case>/ccx/<tag>/")
    ap.add_argument(
        "--ccx-run",
        action="store_true",
        help="Si se activa, ejecuta ccx antes de leer sigma_vm.csv. "
             "Igual necesitas un postproceso que genere sigma_vm.csv.",
    )

    args = ap.parse_args()
    runs_dir = Path(args.runs_dir)

    ensure_case_dirs(args.case, runs_dir)

    geom = pd.read_parquet(geometry_parquet(args.case, args.geom_tag, runs_dir)).copy()
    required = {"elem_id", "cx", "cy", "cz"}
    missing = [c for c in required if c not in geom.columns]
    if missing:
        raise ValueError(f"Faltan columnas {missing} en geometría")

    if args.backend == "fallback":
        sigma_df = _fallback_sigma(
            geom=geom,
            tag=args.tag,
            tipx=args.tipx,
            tipy=args.tipy,
            tipz=args.tipz,
            sigma0=args.sigma0,
            amp=args.amp,
            r0=args.r0,
        )
        note = f"Nota: se usó fallback gaussiano para tag={args.tag}."

    else:  # calculix
        workdir = _normalize_cli_path(args.ccx_workdir) if args.ccx_workdir else _default_ccx_workdir(args.case, runs_dir, args.tag)
        workdir.mkdir(parents=True, exist_ok=True)

        if args.ccx_run:
            inp = workdir / f"{args.ccx_job}.inp"
            if not inp.exists():
                raise FileNotFoundError(f"Falta INP para CalculiX: {inp}")
            run_ccx(args.ccx_exe, args.ccx_job, workdir)

        sigma_path = _normalize_cli_path(args.sigma_file) if args.sigma_file else _default_sigma_csv(args.case, runs_dir, args.tag)
        sigma_path = _normalize_cli_path(sigma_path)

        ext_df = read_sigma_vm_table(sigma_path)

        sigma_df = geom[["elem_id"]].merge(ext_df, on="elem_id", how="left")
        nmiss = int(sigma_df["sigma_vm"].isna().sum())
        if nmiss > 0:
            raise RuntimeError(
                f"CalculiX externo no cubre {nmiss} elementos ({args.tag}). "
                "Revisa mapping elem_id solver <-> geometría."
            )
        note = f"Nota: se usó backend calculix desde {sigma_path}."

    out = sigma_vm_parquet(args.case, args.tag, runs_dir)
    sigma_df.to_parquet(out, index=False)

    print(f"OK: creado {out}")
    print(note)


if __name__ == "__main__":
    main()
