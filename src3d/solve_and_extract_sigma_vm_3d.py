# src3d/solve_and_extract_sigma_vm_3d.py
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src3d.fem.fenics_runner import default_sigma_file
from src3d.fem.parse_results import read_sigma_vm_table
from src3d.paths3d import ensure_case_dirs, geometry_parquet, sigma_vm_parquet


def _fallback_sigma(geom: pd.DataFrame, tag: str, tipx: float, tipy: float, tipz: float, sigma0: float, amp: float, r0: float) -> pd.DataFrame:
    tip = np.array([tipx, tipy, tipz], dtype=float)
    c = geom[["cx", "cy", "cz"]].values.astype(float)
    r = np.linalg.norm(c - tip[None, :], axis=1)

    if tag == "coarse":
        sigma = sigma0 + amp * np.exp(-(r / r0) ** 2)
    else:
        sigma = sigma0 + 0.6 * amp * np.exp(-(r / (1.4 * r0)) ** 2)

    return pd.DataFrame({"elem_id": geom["elem_id"].astype(int), "sigma_vm": sigma.astype(float)})


def _resolve_fenics_path(case: str, runs_dir: str, tag: str, sigma_file: str) -> Path:
    if sigma_file:
        return Path(sigma_file)
    return default_sigma_file(case, runs_dir, tag)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Genera sigma_vm por elemento para tag coarse/ref (fallback o FEM externo)."
    )
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--tag", required=True, choices=["coarse", "ref"])
    ap.add_argument("--geom-tag", default="", help="tag de geometría: '' o 'adapt'")

    ap.add_argument("--backend", choices=["fallback", "fenics_csv"], default="fallback")
    ap.add_argument("--sigma-file", default="", help="Archivo FEM con columnas elem_id,sigma_vm (.csv/.parquet)")

    ap.add_argument("--tipx", type=float, default=0.25)
    ap.add_argument("--tipy", type=float, default=0.50)
    ap.add_argument("--tipz", type=float, default=0.005)
    ap.add_argument("--sigma0", type=float, default=100.0)
    ap.add_argument("--amp", type=float, default=80.0)
    ap.add_argument("--r0", type=float, default=0.08)
    args = ap.parse_args()

    ensure_case_dirs(args.case, args.runs_dir)

    geom = pd.read_parquet(geometry_parquet(args.case, args.geom_tag, args.runs_dir)).copy()
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
        note = f"Nota: se usó fallback reproducible para tag={args.tag}."
    else:
        sigma_path = _resolve_fenics_path(args.case, str(args.runs_dir), args.tag, args.sigma_file)
        ext_df = read_sigma_vm_table(sigma_path)

        sigma_df = geom[["elem_id"]].merge(ext_df, on="elem_id", how="left")
        nmiss = int(sigma_df["sigma_vm"].isna().sum())
        if nmiss > 0:
            raise RuntimeError(
                f"FEM externo no cubre {nmiss} elementos de la malla ({args.tag}). "
                "Revisa mapping elem_id entre solver y geometría."
            )
        note = f"Nota: se usó backend FEM real (fenics_csv) desde {sigma_path}."

    out = sigma_vm_parquet(args.case, args.tag, args.runs_dir)
    sigma_df.to_parquet(out, index=False)

    print(f"OK: creado {out}")
    print(note)


if __name__ == "__main__":
    main()
