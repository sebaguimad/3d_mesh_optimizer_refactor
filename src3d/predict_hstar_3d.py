# src3d/predict_hstar_3d.py
from __future__ import annotations
import argparse
import pandas as pd
import joblib

from src3d.paths3d import (
    ensure_case_dirs,
    rf_model_path,
    dataset_hstar_parquet,
    h_pred_element_parquet,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    args = ap.parse_args()

    ensure_case_dirs(args.case)

    pack = joblib.load(rf_model_path(args.case))
    model = pack["model"]
    feats = pack["features"]

    df = pd.read_parquet(dataset_hstar_parquet(args.case)).copy()
    X = df[feats]

    h_pred = model.predict(X)
    out = h_pred_element_parquet(args.case)

    out_df = df[["elem_id","cx","cy","cz","h_cbrtV","sigma_vm_coarse"]].copy()
    out_df["h_pred"] = h_pred
    out_df.to_parquet(out, index=False)

    print(f"OK: guardado {len(out_df)} tets en: {out}")
    print(out_df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()