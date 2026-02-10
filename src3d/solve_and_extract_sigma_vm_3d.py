# src3d/solve_and_extract_sigma_vm_3d.py
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import pandas as pd

from src3d.paths3d import ensure_case_dirs, geometry_parquet, sigma_vm_parquet


def _read_sigma_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"elem_id", "sigma_vm"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV FEM sin columnas requeridas {missing}: {path}")
    return df[["elem_id", "sigma_vm"]].copy()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extrae sigma_vm por elemento usando FEM real (CalculiX) o CSV intermedio."
    )
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--mesh", required=False, help="msh de entrada (para trazabilidad)")
    ap.add_argument("--tag", required=True, choices=["coarse", "ref"])
    ap.add_argument("--geom-tag", default="", help="tag de geometría: '' o 'adapt'")

    # NUEVO: integración FEM real
    ap.add_argument("--sigma-csv", default="", help="CSV FEM con columnas: elem_id,sigma_vm")
    ap.add_argument("--ccx-exe", default="ccx", help="Ejecutable de CalculiX")
    ap.add_argument("--ccx-job", default="", help="Nombre job sin extensión (si se quiere ejecutar ccx)")
    ap.add_argument("--ccx-workdir", default="", help="Carpeta del .inp/.dat/.frd")

    args = ap.parse_args()
    ensure_case_dirs(args.case, args.runs_dir)

    # Geometría para validar cobertura de elem_id
    geom = pd.read_parquet(geometry_parquet(args.case, args.geom_tag, args.runs_dir)).copy()
    if "elem_id" not in geom.columns:
        raise ValueError("La geometría no contiene elem_id")

    # 1) Opción recomendada: FEM ya exportó CSV elem_id,sigma_vm
    if args.sigma_csv:
        sigma_df = _read_sigma_csv(Path(args.sigma_csv))

    # 2) Opción: ejecutar CalculiX y luego leer CSV generado por tu postproceso
    else:
        if not args.ccx_job:
            raise ValueError("Debes pasar --sigma-csv o bien --ccx-job (+ --ccx-workdir).")

        workdir = Path(args.ccx_workdir) if args.ccx_workdir else Path(".")
        cmd = [args.ccx_exe, "-i", args.ccx_job]
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"CalculiX falló ({proc.returncode}).\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

        # Convención: tu postproceso FEM debe dejar este CSV
        csv_path = workdir / f"{args.ccx_job}_sigma_vm.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"No se encontró {csv_path}. Debes exportar elem_id,sigma_vm desde resultados ccx."
            )
        sigma_df = _read_sigma_csv(csv_path)

    # Validar y alinear con la geometría del pipeline
    sigma_df["elem_id"] = sigma_df["elem_id"].astype(int)
    sigma_df["sigma_vm"] = sigma_df["sigma_vm"].astype(float)

    out_df = geom[["elem_id"]].merge(sigma_df, on="elem_id", how="left")
    n_missing = int(out_df["sigma_vm"].isna().sum())
    if n_missing > 0:
        raise RuntimeError(
            f"Faltan {n_missing} elem_id sin sigma_vm tras merge FEM. "
            "Revisa mapeo de IDs entre solver y malla."
        )

    out = sigma_vm_parquet(args.case, args.tag, args.runs_dir)
    out_df.to_parquet(out, index=False)
    print(f"OK: creado {out} (FEM real)")
    print(out_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
