# src3d/train_ml_hstar_3d.py
from __future__ import annotations
import argparse
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import joblib

from src3d.paths3d import ensure_case_dirs, dataset_hstar_parquet, rf_model_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--random-state", "--random_state", dest="random_state", type=int, default=7)
    ap.add_argument("--n-estimators", "--n_estimators", dest="n_estimators", type=int, default=300)
    args = ap.parse_args()

    ensure_case_dirs(args.case, args.runs_dir)

    df = pd.read_parquet(dataset_hstar_parquet(args.case, args.runs_dir)).copy()

    feats = ["cx", "cy", "cz", "h_cbrtV", "sigma_vm_coarse"]
    for c in feats + ["h_star"]:
        if c not in df.columns:
            raise ValueError(f"Falta columna: {c}")

    X = df[feats]
    y = df["h_star"]

    model = RandomForestRegressor(
        n_estimators=args.n_estimators,
        random_state=args.random_state,
        n_jobs=-1
    )
    model.fit(X, y)

    pred = model.predict(X)
    mse = mean_squared_error(y, pred)
    r2 = r2_score(y, pred)

    out = rf_model_path(args.case, args.runs_dir)
    joblib.dump({"model": model, "features": feats}, out)

    print("OK: entrenamiento terminado")
    print(f"MSE: {mse:.6f}")
    print(f"R2 : {r2:.4f}")

    importances = pd.DataFrame({"feature": feats, "importance": model.feature_importances_}).sort_values("importance", ascending=False)
    print("\nFeature importance:")
    print(importances.to_string(index=False))

    print(f"\nOK: modelo guardado en: {out}")

if __name__ == "__main__":
    main()
