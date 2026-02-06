# src3d/export_background_points_3d.py
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

from src3d.paths3d import (
    ensure_case_dirs,
    h_pred_post_parquet,
    background_csv_path,
    background_pos_path,
)

def write_pos(points_df: pd.DataFrame, out_pos: Path) -> None:
    lines = []
    lines.append('View "background_points_3d" {')
    for _, r in points_df.iterrows():
        x = float(r["x"]); y = float(r["y"]); z = float(r["z"]); h = float(r["h"])
        lines.append(f"  SP({x},{y},{z}){{{h}}};")
    lines.append("};")
    out_pos.write_text("\n".join(lines), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    args = ap.parse_args()

    ensure_case_dirs(args.case)

    hp = pd.read_parquet(h_pred_post_parquet(args.case)).copy()
    required = ["cx","cy","cz","h_post"]
    missing = [c for c in required if c not in hp.columns]
    if missing:
        raise ValueError(f"Faltan columnas {missing} en h_pred_post_3d.parquet")

    pts = hp.rename(columns={"cx":"x","cy":"y","cz":"z","h_post":"h"})[["x","y","z","h"]]

    out_csv = background_csv_path(args.case)
    out_pos = background_pos_path(args.case)
    pts.to_csv(out_csv, index=False)
    write_pos(pts, out_pos)

    print(f"OK: CSV guardado en {out_csv}")
    print(f"OK: POS guardado en {out_pos}")
    print(pts.head(5).to_string(index=False))

if __name__ == "__main__":
    main()