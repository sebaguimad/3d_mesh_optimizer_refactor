# src3d/read_mesh_3d.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

@dataclass
class Mesh3D:
    nodes: Dict[int, Tuple[float, float, float]]     # id -> (x,y,z)
    tets:  List[Tuple[int, int, int, int, int]]      # (elem_id, n1,n2,n3,n4)

def split_prism_to_tets(eid: int, n: List[int]) -> List[Tuple[int,int,int,int,int]]:
    """
    Prisma MSH2 etype=6: 6 nodos (a,b,c,d,e,f)
    base (a,b,c) y tapa (d,e,f).
    Se parte en 3 tetraedros (partición estándar).
    """
    a, b, c, d, e, f = n
    return [
        (eid*10 + 0, a, b, c, d),
        (eid*10 + 1, b, c, e, d),
        (eid*10 + 2, c, e, f, d),
    ]

def read_msh2_3d(path: str | Path) -> Mesh3D:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe .msh: {path}")

    nodes: Dict[int, Tuple[float, float, float]] = {}
    tets: List[Tuple[int, int, int, int, int]] = []

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line == "$Nodes":
            n = int(lines[i + 1].strip())
            for k in range(n):
                parts = lines[i + 2 + k].split()
                nid = int(parts[0])
                x, y, z = map(float, parts[1:4])
                nodes[nid] = (x, y, z)
            i = i + 2 + n

        elif line == "$Elements":
            m = int(lines[i + 1].strip())
            for k in range(m):
                parts = lines[i + 2 + k].split()
                eid = int(parts[0])
                etype = int(parts[1])
                ntags = int(parts[2])
                conn = parts[3 + ntags:]

                # etype 4 = tetra 4 nodes
                if etype == 4 and len(conn) >= 4:
                    n1, n2, n3, n4 = map(int, conn[:4])
                    tets.append((eid, n1, n2, n3, n4))

                # etype 11 = tetra 10 nodes (si aparece). Tomamos solo los 4 vértices.
                elif etype == 11 and len(conn) >= 4:
                    n1, n2, n3, n4 = map(int, conn[:4])
                    tets.append((eid, n1, n2, n3, n4))

                # etype 6 = prism 6 nodes -> convertir a 3 tets
                elif etype == 6 and len(conn) >= 6:
                    nn = list(map(int, conn[:6]))
                    tets.extend(split_prism_to_tets(eid, nn))

            i = i + 2 + m

        else:
            i += 1

    if not nodes or not tets:
        raise RuntimeError(
            f"Malla vacía o sin elementos 3D convertibles (MSH2). "
            f"nodes={len(nodes)}, tets={len(tets)} en {path}"
        )

    return Mesh3D(nodes=nodes, tets=tets)