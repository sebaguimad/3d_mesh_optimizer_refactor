# src3d/compute_element_geometry_3d.py
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd

from src3d.paths3d import ensure_case_dirs, geometry_parquet
from src3d.read_mesh_3d import read_msh2_3d

def tet_volume(p1, p2, p3, p4) -> float:
    a = np.array(p2) - np.array(p1)
    b = np.array(p3) - np.array(p1)
    c = np.array(p4) - np.array(p1)
    return float(abs(np.linalg.det(np.vstack([a, b, c]).T)) / 6.0)

def dist(p, q) -> float:
    p = np.array(p); q = np.array(q)
    return float(np.linalg.norm(p - q))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--msh", required=True)
    ap.add_argument("--tag", default="", help="sufijo opcional: adapt, ref, etc.")
    args = ap.parse_args()

    case_dir, gmsh_dir, models_dir = ensure_case_dirs(args.case)

    mesh = read_msh2_3d(args.msh)

    rows = []
    for idx, (_eid, n1, n2, n3, n4) in enumerate(mesh.tets):
        p1 = mesh.nodes[n1]
        p2 = mesh.nodes[n2]
        p3 = mesh.nodes[n3]
        p4 = mesh.nodes[n4]

        cx = (p1[0] + p2[0] + p3[0] + p4[0]) / 4.0
        cy = (p1[1] + p2[1] + p3[1] + p4[1]) / 4.0
        cz = (p1[2] + p2[2] + p3[2] + p4[2]) / 4.0

        vol = tet_volume(p1, p2, p3, p4)

        # 6 edges
        e12 = dist(p1, p2)
        e13 = dist(p1, p3)
        e14 = dist(p1, p4)
        e23 = dist(p2, p3)
        e24 = dist(p2, p4)
        e34 = dist(p3, p4)
        sum_e2 = e12**2 + e13**2 + e14**2 + e23**2 + e24**2 + e34**2

        h_cbrtV = float(vol ** (1.0/3.0)) if vol > 0 else 0.0
        h_mean_edge = float((e12 + e13 + e14 + e23 + e24 + e34) / 6.0)

        quality = float((vol ** (2.0/3.0)) / sum_e2) if (vol > 0 and sum_e2 > 0) else 0.0

        rows.append({
            "elem_id": idx,
            "n0": n1, "n1": n2, "n2": n3, "n3": n4,
            "cx": cx, "cy": cy, "cz": cz,
            "volume": vol,
            "h_cbrtV": h_cbrtV,
            "h_mean_edge": h_mean_edge,
            "quality": quality,
        })

    df = pd.DataFrame(rows)
    out = geometry_parquet(args.case, args.tag)
    df.to_parquet(out, index=False)

    print(f"OK: guardado {len(df)} tets en: {out}")
    print(df.head(8).to_string(index=False))

if __name__ == "__main__":
    main()