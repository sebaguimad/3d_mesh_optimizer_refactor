from __future__ import annotations

import argparse
import numpy as np
import pandas as pd

from src3d.paths3d import ensure_case_dirs, geometry_parquet, sigma_vm_parquet


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Genera sigma_vm por elemento para tag coarse/ref (fallback reproducible)."
    )
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--mesh", required=False, help="Reservado para solver FEM real")
    ap.add_argument("--tag", required=True, choices=["coarse", "ref"])
    ap.add_argument("--geom-tag", default="", help="tag de geometría: '' o 'adapt'")
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

    tip = np.array([args.tipx, args.tipy, args.tipz], dtype=float)
    c = geom[["cx", "cy", "cz"]].values.astype(float)
    r = np.linalg.norm(c - tip[None, :], axis=1)

    if args.tag == "coarse":
        sigma = args.sigma0 + args.amp * np.exp(-(r / args.r0) ** 2)
    else:
        sigma = args.sigma0 + 0.6 * args.amp * np.exp(-(r / (1.4 * args.r0)) ** 2)

    out = sigma_vm_parquet(args.case, args.tag, args.runs_dir)
    pd.DataFrame({"elem_id": geom["elem_id"].astype(int), "sigma_vm": sigma}).to_parquet(out, index=False)

    print(f"OK: creado {out}")
    print(
        f"Nota: se usó fallback reproducible para tag={args.tag}. "
        "Integra aquí tu solver FEM real si aplica."
    )


if __name__ == "__main__":
    main()