# src3d/compute_hstar_3d.py
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd

from src3d.paths3d import (
    ensure_case_dirs,
    geometry_parquet,
    sigma_vm_parquet,
    dataset_hstar_parquet,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--geom_tag", default="", help="tag de geometría: '' o 'adapt'")
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--hmin", type=float, default=None)
    ap.add_argument("--hmax", type=float, default=None)
    ap.add_argument("--eps", type=float, default=1e-12)
    args = ap.parse_args()

    case_dir, gmsh_dir, models_dir = ensure_case_dirs(args.case, args.runs_dir)

    geom = pd.read_parquet(geometry_parquet(args.case, args.geom_tag, args.runs_dir)).copy()
    sc = pd.read_parquet(sigma_vm_parquet(args.case, "coarse", args.runs_dir)).rename(columns={"sigma_vm": "sigma_vm_coarse"})
    sr = pd.read_parquet(sigma_vm_parquet(args.case, "ref", args.runs_dir)).rename(columns={"sigma_vm": "sigma_vm_ref"})

    df = geom.merge(sc, on="elem_id", how="inner").merge(sr, on="elem_id", how="inner")
    if len(df) == 0:
        raise RuntimeError("Merge vacío: revisa elem_id y archivos sigma.")

    e_rel = np.abs(df["sigma_vm_coarse"].values - df["sigma_vm_ref"].values) / (np.abs(df["sigma_vm_ref"].values) + args.eps)
    df["e_rel"] = e_rel

    h0 = df["h_cbrtV"].values.astype(float)
    h_med = float(np.median(h0))

    hmin = args.hmin if args.hmin is not None else 0.6 * h_med
    hmax = args.hmax if args.hmax is not None else 1.2 * h_med

    factor = (args.tol / (df["e_rel"].values + args.eps)) ** args.alpha
    h_star = np.clip(h0 * factor, hmin, hmax)
    df["h_star"] = h_star

    out = dataset_hstar_parquet(args.case, args.runs_dir)
    df.to_parquet(out, index=False)

    print(f"OK: merged rows = {len(df)}")
    print(f"e_rel: min={df['e_rel'].min():.3e}, median={df['e_rel'].median():.3e}, max={df['e_rel'].max():.3e}")
    print(f"h_star: min={df['h_star'].min():.4f}, median={df['h_star'].median():.4f}, max={df['h_star'].max():.4f}")
    print(f"OK: guardado dataset con h*: {out}")
    print(df[["elem_id","cx","cy","cz","h_cbrtV","sigma_vm_coarse","sigma_vm_ref","e_rel","h_star"]].head(10).to_string(index=False))

if __name__ == "__main__":
    main()