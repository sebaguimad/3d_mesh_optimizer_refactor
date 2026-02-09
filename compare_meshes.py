from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


def read_msh2_ascii(path: Path) -> Tuple[np.ndarray, Dict[int, np.ndarray]]:
    """
    Returns:
      nodes: (N,3) float64
      elems: dict gmsh_elem_type -> connectivity (M,k) int64 (1-based node ids)
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    if not any("$MeshFormat" in ln for ln in lines[:10]):
        raise ValueError(f"{path} doesn't look like a .msh file (missing $MeshFormat).")

    mesh_format_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "$MeshFormat")
    fmt_line = lines[mesh_format_idx + 1].strip().split()
    if len(fmt_line) >= 2 and fmt_line[1] != "0":
        raise ValueError(
            f"{path} looks binary (MSH2 file_type={fmt_line[1]}). "
            f"Re-export as ASCII:\n"
            f"  gmsh {path} -save -format msh2 -bin 0 -o {path.with_suffix('.ascii.msh')}"
        )

    try:
        n_start = next(i for i, ln in enumerate(lines) if ln.strip() == "$Nodes")
    except StopIteration:
        raise ValueError(f"{path} missing $Nodes section.")
    n_nodes = int(lines[n_start + 1].strip())
    node_block = lines[n_start + 2 : n_start + 2 + n_nodes]
    node_ids = np.empty(n_nodes, dtype=np.int64)
    nodes = np.empty((n_nodes, 3), dtype=np.float64)
    for i, ln in enumerate(node_block):
        parts = ln.strip().split()
        node_ids[i] = int(parts[0])
        nodes[i, 0] = float(parts[1])
        nodes[i, 1] = float(parts[2])
        nodes[i, 2] = float(parts[3])

    max_id = int(node_ids.max())
    id_to_idx = np.full(max_id + 1, -1, dtype=np.int64)
    id_to_idx[node_ids] = np.arange(n_nodes, dtype=np.int64)

    try:
        e_start = next(i for i, ln in enumerate(lines) if ln.strip() == "$Elements")
    except StopIteration:
        raise ValueError(f"{path} missing $Elements section.")
    n_elems = int(lines[e_start + 1].strip())
    elem_block = lines[e_start + 2 : e_start + 2 + n_elems]

    buckets: Dict[int, List[List[int]]] = {}
    for ln in elem_block:
        parts = ln.strip().split()
        if len(parts) < 4:
            continue
        elem_type = int(parts[1])
        n_tags = int(parts[2])
        node_list = parts[3 + n_tags :]
        conn = [int(x) for x in node_list]
        buckets.setdefault(elem_type, []).append(conn)

    elems: Dict[int, np.ndarray] = {}
    for t, conns in buckets.items():
        elems[t] = np.array(conns, dtype=np.int64)

    for t, conn in elems.items():
        if conn.size == 0:
            continue
        if conn.max() > max_id:
            raise ValueError(f"{path}: element connectivity refers to node id > max node id.")
        idx = id_to_idx[conn]
        if (idx < 0).any():
            bad = conn[idx < 0][0]
            raise ValueError(f"{path}: element refers to missing node id {bad}.")
        elems[t] = idx

    return nodes, elems


def tetra_volume(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    v = np.einsum("ij,ij->i", (b - a), np.cross((c - a), (d - a)))
    return np.abs(v) / 6.0


def tetra_mean_ratio_quality(pts: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """
    Mean ratio quality in [0,1] (higher is better).
    q = (12 * (3V)^(2/3)) / sum(edge_length^2)
    where V is tetra volume, sum over 6 edges.
    """
    p0 = pts[tets[:, 0]]
    p1 = pts[tets[:, 1]]
    p2 = pts[tets[:, 2]]
    p3 = pts[tets[:, 3]]

    v = tetra_volume(p0, p1, p2, p3)

    def lsq(x, y):
        d = x - y
        return np.einsum("ij,ij->i", d, d)

    l01 = lsq(p0, p1)
    l02 = lsq(p0, p2)
    l03 = lsq(p0, p3)
    l12 = lsq(p1, p2)
    l13 = lsq(p1, p3)
    l23 = lsq(p2, p3)
    sum_l2 = l01 + l02 + l03 + l12 + l13 + l23

    eps = 1e-30
    q = (12.0 * np.power(3.0 * np.maximum(v, 0.0), 2.0 / 3.0)) / np.maximum(sum_l2, eps)
    return np.clip(q, 0.0, 1.0)


def unique_edge_lengths(pts: np.ndarray, tets: np.ndarray, max_edges: int = 2_000_000) -> np.ndarray:
    edges = np.stack(
        [
            tets[:, [0, 1]],
            tets[:, [0, 2]],
            tets[:, [0, 3]],
            tets[:, [1, 2]],
            tets[:, [1, 3]],
            tets[:, [2, 3]],
        ],
        axis=1,
    ).reshape(-1, 2)

    edges = np.sort(edges, axis=1)

    if edges.shape[0] > max_edges:
        idx = np.random.choice(edges.shape[0], size=max_edges, replace=False)
        edges = edges[idx]

    edges = np.unique(edges, axis=0)

    p_a = pts[edges[:, 0]]
    p_b = pts[edges[:, 1]]
    return np.linalg.norm(p_a - p_b, axis=1)


@dataclass
class MeshStats:
    path: str
    n_nodes: int
    n_elems: int
    elem_counts: Dict[str, int]
    bbox_min: List[float]
    bbox_max: List[float]
    tet_quality: Dict[str, float] | None
    edge_lengths: Dict[str, float] | None


def compute_stats(path: Path) -> Tuple[MeshStats, Dict[str, np.ndarray]]:
    pts, elems = read_msh2_ascii(path)

    elem_counts: Dict[str, int] = {}
    total_elems = 0
    for etype, conn in elems.items():
        total_elems += int(conn.shape[0])
        elem_counts[f"type_{etype}"] = int(conn.shape[0])

    bbox_min = pts.min(axis=0).tolist()
    bbox_max = pts.max(axis=0).tolist()

    tet_quality_summary = None
    edge_len_summary = None
    arrays_out: Dict[str, np.ndarray] = {"points": pts}

    if 4 in elems and elems[4].shape[0] > 0:
        tets = elems[4]
        q = tetra_mean_ratio_quality(pts, tets)
        arrays_out["tet_quality"] = q
        arrays_out["tets"] = tets

        tet_quality_summary = {
            "min": float(q.min()),
            "p01": float(np.quantile(q, 0.01)),
            "p05": float(np.quantile(q, 0.05)),
            "median": float(np.quantile(q, 0.50)),
            "mean": float(q.mean()),
            "p95": float(np.quantile(q, 0.95)),
            "p99": float(np.quantile(q, 0.99)),
        }

        edge_lengths = unique_edge_lengths(pts, tets)
        arrays_out["edge_lengths"] = edge_lengths
        edge_len_summary = {
            "min": float(edge_lengths.min()),
            "p05": float(np.quantile(edge_lengths, 0.05)),
            "median": float(np.quantile(edge_lengths, 0.50)),
            "mean": float(edge_lengths.mean()),
            "p95": float(np.quantile(edge_lengths, 0.95)),
            "max": float(edge_lengths.max()),
        }

    stats = MeshStats(
        path=str(path),
        n_nodes=int(pts.shape[0]),
        n_elems=int(total_elems),
        elem_counts=elem_counts,
        bbox_min=bbox_min,
        bbox_max=bbox_max,
        tet_quality=tet_quality_summary,
        edge_lengths=edge_len_summary,
    )
    return stats, arrays_out


def save_histograms(
    outdir: Path,
    coarse_name: str,
    adapt_name: str,
    qc: np.ndarray | None,
    qa: np.ndarray | None,
    lc: np.ndarray | None,
    la: np.ndarray | None,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    if qc is not None and qa is not None:
        plt.figure()
        bins = np.linspace(0.0, 1.0, 41)
        plt.hist(qc, bins=bins, alpha=0.6, label=coarse_name, density=True)
        plt.hist(qa, bins=bins, alpha=0.6, label=adapt_name, density=True)
        plt.xlabel("Tetra quality (mean-ratio, 0..1)")
        plt.ylabel("Density")
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / "quality_hist.png", dpi=200)
        plt.close()

    if lc is not None and la is not None:
        plt.figure()
        l_all = np.concatenate([lc, la])
        lo = np.quantile(l_all, 0.001)
        hi = np.quantile(l_all, 0.999)
        if hi <= lo:
            lo = float(l_all.min())
            hi = float(l_all.max())
        bins = np.linspace(lo, hi, 60)

        plt.hist(lc, bins=bins, alpha=0.6, label=coarse_name, density=True)
        plt.hist(la, bins=bins, alpha=0.6, label=adapt_name, density=True)
        plt.xlabel("Unique edge length")
        plt.ylabel("Density")
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / "edge_length_hist.png", dpi=200)
        plt.close()


def print_report(coarse: MeshStats, adapt: MeshStats) -> None:
    def fmt(x: float) -> str:
        return f"{x:.6g}"

    print("\n====================")
    print("COARSE vs ADAPT REPORT")
    print("====================\n")

    print(f"Coarse: {coarse.path}")
    print(f"Adapt : {adapt.path}\n")

    print("Counts:")
    print(f"  Nodes      : {coarse.n_nodes}  ->  {adapt.n_nodes}   (x{adapt.n_nodes/max(coarse.n_nodes,1):.2f})")
    print(f"  Elements   : {coarse.n_elems}  ->  {adapt.n_elems}   (x{adapt.n_elems/max(coarse.n_elems,1):.2f})")
    print(f"  Elem types : coarse {coarse.elem_counts}")
    print(f"              adapt  {adapt.elem_counts}\n")

    print("Bounding box (min -> max):")
    print(f"  Coarse: {list(map(fmt, coarse.bbox_min))} -> {list(map(fmt, coarse.bbox_max))}")
    print(f"  Adapt : {list(map(fmt, adapt.bbox_min))} -> {list(map(fmt, adapt.bbox_max))}\n")

    if coarse.tet_quality and adapt.tet_quality:
        print("Tetra quality (mean-ratio, 0..1):")
        for k in ["min", "p01", "p05", "median", "mean", "p95", "p99"]:
            print(f"  {k:>6}: {fmt(coarse.tet_quality[k])}  ->  {fmt(adapt.tet_quality[k])}")
        print("  (Higher is better; watch especially p01/p05 and min)\n")
    else:
        print("No tetra quality computed (missing tets?).\n")

    if coarse.edge_lengths and adapt.edge_lengths:
        print("Edge length (unique edges):")
        for k in ["min", "p05", "median", "mean", "p95", "max"]:
            print(f"  {k:>6}: {fmt(coarse.edge_lengths[k])}  ->  {fmt(adapt.edge_lengths[k])}")
        print("  (Adapt should usually shift distribution to smaller lengths in refined zones)\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coarse", required=True, help="Path to coarse_3d.msh (MSH2 ASCII recommended)")
    ap.add_argument("--adapt", required=True, help="Path to adapt_3d.msh (MSH2 ASCII recommended)")
    ap.add_argument("--outdir", default="mesh_compare_out", help="Output folder for plots + json")
    args = ap.parse_args()

    coarse_path = Path(args.coarse)
    adapt_path = Path(args.adapt)
    outdir = Path(args.outdir)

    coarse_stats, coarse_arrays = compute_stats(coarse_path)
    adapt_stats, adapt_arrays = compute_stats(adapt_path)

    print_report(coarse_stats, adapt_stats)

    outdir.mkdir(parents=True, exist_ok=True)
    with (outdir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({"coarse": coarse_stats.__dict__, "adapt": adapt_stats.__dict__}, f, indent=2)

    qc = coarse_arrays.get("tet_quality", None)
    qa = adapt_arrays.get("tet_quality", None)
    lc = coarse_arrays.get("edge_lengths", None)
    la = adapt_arrays.get("edge_lengths", None)

    save_histograms(
        outdir=outdir,
        coarse_name="coarse",
        adapt_name="adapt",
        qc=qc,
        qa=qa,
        lc=lc,
        la=la,
    )

    print(f"Saved:\n  {outdir / 'summary.json'}")
    if (outdir / "quality_hist.png").exists():
        print(f"  {outdir / 'quality_hist.png'}")
    if (outdir / "edge_length_hist.png").exists():
        print(f"  {outdir / 'edge_length_hist.png'}")
    print("Done.\n")


if __name__ == "__main__":
    main()