# src3d/make_dummy_sigma_vm_3d.py
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd

from src3d.paths3d import ensure_case_dirs, geometry_parquet, sigma_vm_parquet

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--geom_tag", default="", help="tag de geometría: '' o 'adapt'")
    ap.add_argument("--tipx", type=float, default=0.25)
    ap.add_argument("--tipy", type=float, default=0.5)
    ap.add_argument("--tipz", type=float, default=0.005)
    ap.add_argument("--sigma0", type=float, default=100.0)
    ap.add_argument("--amp", type=float, default=80.0)
    ap.add_argument("--r0", type=float, default=0.08)
    args = ap.parse_args()

    case_dir, gmsh_dir, models_dir = ensure_case_dirs(args.case, args.runs_dir)

    geom = pd.read_parquet(geometry_parquet(args.case, args.geom_tag, args.runs_dir)).copy()

    tip = np.array([args.tipx, args.tipy, args.tipz], dtype=float)
    c = geom[["cx", "cy", "cz"]].values.astype(float)
    r = np.linalg.norm(c - tip[None, :], axis=1)

    sigma_coarse = args.sigma0 + args.amp * np.exp(-(r / args.r0) ** 2)
    sigma_ref = args.sigma0 + 0.6 * args.amp * np.exp(-(r / (1.4 * args.r0)) ** 2)

    out_c = sigma_vm_parquet(args.case, "coarse", args.runs_dir)
    out_r = sigma_vm_parquet(args.case, "ref", args.runs_dir)

    pd.DataFrame({"elem_id": geom["elem_id"].astype(int), "sigma_vm": sigma_coarse}).to_parquet(out_c, index=False)
    pd.DataFrame({"elem_id": geom["elem_id"].astype(int), "sigma_vm": sigma_ref}).to_parquet(out_r, index=False)

    print(f"OK: creado {out_c}")
    print(f"OK: creado {out_r}")
    print(pd.DataFrame({"elem_id": geom["elem_id"].head(5), "sigma_vm": sigma_coarse[:5]}).to_string(index=False))

if __name__ == "__main__":
    main()