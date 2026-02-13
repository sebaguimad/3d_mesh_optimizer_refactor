# parse_results.py
from __future__ import annotations

from pathlib import Path

import pandas as pd

def _normalize_input_path(path: Path) -> Path:
    """Normaliza rutas provenientes de CLI (espacios/comillas accidentales)."""
    clean = str(path).strip().strip('"').strip("'")
    return Path(clean).expanduser()

def read_sigma_vm_table(path: Path) -> pd.DataFrame:
    """
    Lee resultados FEM por elemento y valida contrato mínimo:
      - elem_id (int)
      - sigma_vm (float)
    Soporta CSV o Parquet.
    """
    path = _normalize_input_path(path)
    if not path.exists():
        cwd = Path.cwd()
        raise FileNotFoundError(
            "No existe archivo FEM: "
            f"{path} (cwd={cwd}). "
            "Verifica la ruta o usa una ruta absoluta válida."
        )

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Formato FEM no soportado: {path.suffix}. Usa .csv o .parquet")

    required = {"elem_id", "sigma_vm"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas {missing} en {path}")

    out = df[["elem_id", "sigma_vm"]].copy()
    out["elem_id"] = out["elem_id"].astype(int)
    out["sigma_vm"] = out["sigma_vm"].astype(float)

    if out["elem_id"].duplicated().any():
        ndup = int(out["elem_id"].duplicated().sum())
        raise ValueError(f"Hay elem_id duplicados en FEM ({ndup}) en {path}")

    return out
