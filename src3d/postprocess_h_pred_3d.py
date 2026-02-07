# src3d/postprocess_h_pred_3d.py
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd

from src3d.paths3d import (
    ensure_case_dirs,
    h_pred_element_parquet,
    geometry_parquet,
    h_pred_post_parquet,
)

def pick_h_column(df: pd.DataFrame) -> str:
    """
    Encuentra una columna válida de tamaño base (h_cbrtV) aunque
    haya quedado con sufijos tras merges.
    """
    candidates = [
        "h_cbrtV",
        "h_cbrtV_geom",
        "h_cbrtV_x",
        "h_cbrtV_y",
        "h_cbrtV_coarse",
        "h_cbrtV_adapt",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    # fallback: cualquier columna que empiece con h_cbrtV
    for c in df.columns:
        if str(c).startswith("h_cbrtV"):
            return c
    raise KeyError(f"No encontré columna h_cbrtV en df. Columnas: {list(df.columns)}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--min_factor", type=float, default=0.6)   # hmin = min_factor * h_med
    ap.add_argument("--max_factor", type=float, default=1.2)   # hmax = max_factor * h_med
    ap.add_argument("--q_low", type=float, default=0.02)       # winsor
    ap.add_argument("--q_high", type=float, default=0.98)
    args = ap.parse_args()

    case_dir, gmsh_dir, models_dir = ensure_case_dirs(args.case, args.runs_dir)

    # pred trae: elem_id,cx,cy,cz,h_cbrtV?,sigma_vm_coarse,h_pred
    pred = pd.read_parquet(h_pred_element_parquet(args.case, args.runs_dir)).copy()

    # geom siempre trae el h base "oficial" de la malla coarse
    geom = pd.read_parquet(geometry_parquet(args.case, tag="", runs_dir=args.runs_dir))[["elem_id", "h_cbrtV"]].copy()
    geom = geom.rename(columns={"h_cbrtV": "h_cbrtV_geom"})

    df = pred.merge(geom, on="elem_id", how="left")

    # elegir columna de h base (preferimos h_cbrtV_geom si existe)
    hcol = "h_cbrtV_geom" if "h_cbrtV_geom" in df.columns else pick_h_column(df)

    if df[hcol].isna().any():
        nmiss = int(df[hcol].isna().sum())
        raise RuntimeError(
            f"Merge pred+geom dejó {nmiss} filas sin h base ({hcol}). "
            "Revisa que elem_id coincida entre h_pred_element_3d y element_geometry_3d."
        )

    h0 = df[hcol].to_numpy(dtype=float)

    h_med = float(np.median(h0))
    hmin = float(args.min_factor * h_med)
    hmax = float(args.max_factor * h_med)

    # winsor sobre h_pred
    ql = float(df["h_pred"].quantile(args.q_low))
    qh = float(df["h_pred"].quantile(args.q_high))
    h = df["h_pred"].clip(lower=ql, upper=qh)

    # clamp final físico
    h_post = h.clip(lower=hmin, upper=hmax)
    df["h_post"] = h_post

    out = h_pred_post_parquet(args.case, args.runs_dir)
    df[["elem_id", "cx", "cy", "cz", "h_pred", "h_post"]].to_parquet(out, index=False)

    print(f"OK: post-proceso guardado en: {out}")
    print(f"h_base_col  = {hcol}")
    print(f"h_med       = {h_med}")
    print(f"hmin/hmax   = {hmin} {hmax}")
    print("h_post stats:\n", df["h_post"].describe())
    print(df[["elem_id", "h_pred", "h_post"]].head(10).to_string(index=False))

if __name__ == "__main__":
    main()