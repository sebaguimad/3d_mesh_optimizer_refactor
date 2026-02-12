# src3d/train_ml_hstar_3d.py
from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from src3d.paths3d import ensure_case_dirs, dataset_hstar_parquet, rf_model_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--n_estimators", type=int, default=400)
    ap.add_argument("--random_state", type=int, default=7)
    ap.add_argument("--test_size", type=float, default=0.2)
    args = ap.parse_args()

    if not (0.0 < args.test_size < 1.0):
        raise ValueError("test_size debe estar en el rango (0, 1).")

    ensure_case_dirs(args.case, args.runs_dir)

    df = pd.read_parquet(dataset_hstar_parquet(args.case, args.runs_dir)).copy()

    feats = ["cx", "cy", "cz", "h_cbrtV", "sigma_vm_coarse"]
    for c in feats + ["h_star"]:
        if c not in df.columns:
            raise ValueError(f"Falta columna: {c}")

    X = df[feats]
    y = df["h_star"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    model = RandomForestRegressor(
        n_estimators=args.n_estimators,
        random_state=args.random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)

    train_mse = mean_squared_error(y_train, train_pred)
    train_r2 = r2_score(y_train, train_pred)
    test_mse = mean_squared_error(y_test, test_pred)
    test_r2 = r2_score(y_test, test_pred)

    out = rf_model_path(args.case, args.runs_dir)
    joblib.dump({"model": model, "features": feats}, out)

    print("OK: entrenamiento terminado")
    print(f"Train size: {len(X_train)} | Test size: {len(X_test)}")
    print(f"Train MSE: {train_mse:.6f}")
    print(f"Train R2 : {train_r2:.4f}")
    print(f"Test MSE : {test_mse:.6f}")
    print(f"Test R2  : {test_r2:.4f}")

    importances = pd.DataFrame(
        {"feature": feats, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)
    print("\nFeature importance:")
    print(importances.to_string(index=False))

    print(f"\nOK: modelo guardado en: {out}")


if __name__ == "__main__":
    main()
