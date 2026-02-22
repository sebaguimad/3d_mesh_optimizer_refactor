from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from src3d.fem.calculix_runner import run_ccx
from src3d.fem.cgx_extract_sigma_vm import run_cgx, write_cgx_script
from src3d.fem.parse_results import read_sigma_vm_table
from src3d.paths3d import ensure_case_dirs, geometry_parquet, sigma_vm_parquet


def _normalize_cli_path(path: Path | str) -> Path:
    clean = str(path).strip().strip('"').strip("'")
    return Path(clean).expanduser()


def _fallback_sigma(
    geom: pd.DataFrame,
    tag: str,
    tipx: float,
    tipy: float,
    tipz: float,
    sigma0: float,
    amp: float,
    r0: float,
) -> pd.DataFrame:
    """
    Fallback gaussiano:
    genera un "hotspot" de tensión alrededor del punto (tipx,tipy,tipz).
    Sirve para probar el pipeline sin solver FEM real.
    """
    tip = np.array([tipx, tipy, tipz], dtype=float)
    centers = geom[["cx", "cy", "cz"]].values.astype(float)
    r = np.linalg.norm(centers - tip[None, :], axis=1)

    if tag == "coarse":
        sigma = sigma0 + amp * np.exp(-(r / r0) ** 2)
    else:
        sigma = sigma0 + 0.6 * amp * np.exp(-(r / (1.4 * r0)) ** 2)

    return pd.DataFrame(
        {"elem_id": geom["elem_id"].astype(int), "sigma_vm": sigma.astype(float)}
    )


def _default_ccx_workdir(case: str, runs_dir: str | Path, tag: str) -> Path:
    # runs/<case>/ccx/<tag>/
    return Path(runs_dir) / case / "ccx" / tag


def _default_sigma_csv(case: str, runs_dir: str | Path, tag: str) -> Path:
    # runs/<case>/ccx/<tag>/sigma_vm.csv
    return _default_ccx_workdir(case, runs_dir, tag) / "sigma_vm.csv"


_NODE_LINE_RE = re.compile(
    r"^\s*(\d+)\s*,\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*,\s*"
    r"([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*,\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*$"
)
_ELEM_LINE_RE = re.compile(r"^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*$")


def _export_mesh_inp_from_msh(*, gmsh_exe: str, msh_path: Path, out_inp: Path) -> None:
    out_inp.parent.mkdir(parents=True, exist_ok=True)
    cmd = [gmsh_exe, str(msh_path), "-format", "inp", "-o", str(out_inp)]
    print(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def _read_nodes_from_inp(mesh_inp: Path) -> pd.DataFrame:
    """Lee bloque *NODE de INP exportado por Gmsh."""
    lines = mesh_inp.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_node = False
    rows: list[tuple[int, float, float, float]] = []

    for line in lines:
        row = line.strip()
        if not row:
            continue
        if row.upper().startswith("*NODE"):
            in_node = True
            continue
        if in_node and row.startswith("*"):
            break
        if in_node:
            m = _NODE_LINE_RE.match(row)
            if m:
                rows.append(
                    (
                        int(m.group(1)),
                        float(m.group(2)),
                        float(m.group(3)),
                        float(m.group(4)),
                    )
                )

    if not rows:
        raise RuntimeError(f"No pude leer nodos desde {mesh_inp}. Verifica bloque *NODE.")
    return pd.DataFrame(rows, columns=["node_id", "x", "y", "z"])


def _read_elements_from_inp(mesh_inp: Path) -> pd.DataFrame:
    """Lee el primer bloque *ELEMENT tetra4 del INP."""
    lines = mesh_inp.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_elem = False
    rows: list[tuple[int, int, int, int, int]] = []

    for line in lines:
        row = line.strip()
        if not row:
            continue
        if row.upper().startswith("*ELEMENT"):
            in_elem = True
            continue
        if in_elem and row.startswith("*"):
            break
        if in_elem:
            m = _ELEM_LINE_RE.match(row)
            if m:
                rows.append(
                    (
                        int(m.group(1)),
                        int(m.group(2)),
                        int(m.group(3)),
                        int(m.group(4)),
                        int(m.group(5)),
                    )
                )

    if not rows:
        raise RuntimeError(
            f"No pude leer elementos tetra4 desde {mesh_inp}. "
            "Si tu INP usa otro tipo de elemento, ajusta el parser."
        )
    return pd.DataFrame(rows, columns=["elem_id", "n1", "n2", "n3", "n4"])


def _pick_face_nodes(nodes: pd.DataFrame, *, axis: str, side: str, tol: float) -> np.ndarray:
    axis = axis.lower().strip()
    side = side.lower().strip()
    if axis not in {"x", "y", "z"}:
        raise ValueError("axis debe ser x|y|z")
    if side not in {"min", "max"}:
        raise ValueError("side debe ser min|max")

    values = nodes[axis].to_numpy(dtype=float)
    target = float(np.min(values) if side == "min" else np.max(values))
    selected = nodes.loc[np.abs(values - target) <= float(tol), "node_id"].to_numpy(dtype=int)

    if selected.size == 0:
        raise RuntimeError(
            f"No se seleccionaron nodos para cara {axis}-{side} con tol={tol}. "
            "Prueba aumentar --face-tol."
        )
    return selected


def _format_id_list(ids: Iterable[int], *, per_line: int = 16) -> str:
    vals = [int(v) for v in ids]
    lines = []
    for i in range(0, len(vals), per_line):
        chunk = vals[i : i + per_line]
        lines.append(", ".join(str(v) for v in chunk))
    return "\n".join(lines)


def _autogen_job_inp(
    *,
    workdir: Path,
    ccx_job: str,
    case: str,
    tag: str,
    mesh_inp_name: str,
    nodes: pd.DataFrame,
    elems: pd.DataFrame,
    mat_name: str,
    mat_e: float,
    mat_nu: float,
    fix_axis: str,
    fix_side: str,
    load_axis: str,
    load_side: str,
    face_tol: float,
    load_f_total: float,
) -> Path:
    """
    Crea <ccx_job>.inp con defaults:
    - include de mesh.inp
    - ELSET completo
    - NSET fijo en una cara del bounding-box
    - NSET cargado en la cara opuesta (o configurable)
    - material lineal isotrópico + solid section
    - *BOUNDARY y *CLOAD nodal distribuido
    """
    fix_nodes = _pick_face_nodes(nodes, axis=fix_axis, side=fix_side, tol=face_tol)
    load_nodes = _pick_face_nodes(nodes, axis=load_axis, side=load_side, tol=face_tol)
    eall = elems["elem_id"].to_numpy(dtype=int)

    dof_by_axis = {"x": 1, "y": 2, "z": 3}
    load_dof = dof_by_axis[load_axis.lower()]
    f_per_node = float(load_f_total) / float(len(load_nodes))

    lines = [
        "*HEADING",
        f"{case} - {tag} - autogenerated job.inp",
        "",
        f"*INCLUDE, INPUT={mesh_inp_name}",
        "",
        "*ELSET, ELSET=EALL",
        _format_id_list(eall),
        "*NSET, NSET=NSET_FIX",
        _format_id_list(fix_nodes),
        "*NSET, NSET=NSET_LOAD",
        _format_id_list(load_nodes),
        "",
        f"*MATERIAL, NAME={mat_name}",
        "*ELASTIC",
        f"{mat_e}, {mat_nu}",
        f"*SOLID SECTION, ELSET=EALL, MATERIAL={mat_name}",
        "",
        "*STEP",
        "*STATIC",
        "*BOUNDARY",
        "NSET_FIX, 1, 3, 0.0",
        "*CLOAD",
    ]
    lines.extend(f"{nid}, {load_dof}, {f_per_node}" for nid in load_nodes)
    lines.extend(
        [
            "*EL FILE",
            "S, E",
            "*NODE FILE",
            "U",
            "*END STEP",
            "",
        ]
    )

    job_inp = workdir / f"{ccx_job}.inp"
    job_inp.write_text("\n".join(lines), encoding="utf-8")
    return job_inp


def _guess_msh_path(case: str, runs_dir: Path, tag: str) -> Path:
    candidates = [
        runs_dir / case / "gmsh" / f"{tag}_3d.msh",
        runs_dir / case / "gmsh" / "coarse_3d.msh",
        runs_dir / case / "gmsh" / "ref_3d.msh",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "No pude autogenerar mesh.inp porque no encontré un .msh en runs/<case>/gmsh "
        f"(probé: {', '.join(str(c) for c in candidates)})."
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Genera sigma_vm por elemento para tag coarse/ref (fallback o CalculiX)."
    )
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--tag", required=True, choices=["coarse", "ref"])
    ap.add_argument("--geom-tag", default="", help="tag de geometría: '' o 'adapt'")

    ap.add_argument("--backend", choices=["fallback", "calculix"], default="fallback")

    # Entrada genérica para FEM externo (CalculiX/ANSYS): CSV/Parquet con elem_id,sigma_vm
    ap.add_argument(
        "--sigma-file",
        default="",
        help="(FEM externo) Archivo elem_id,sigma_vm (.csv/.parquet). "
        "Si no se da: runs/<case>/ccx/<tag>/sigma_vm.csv",
    )

    # Fallback params
    ap.add_argument("--tipx", type=float, default=0.25)
    ap.add_argument("--tipy", type=float, default=0.50)
    ap.add_argument("--tipz", type=float, default=0.005)
    ap.add_argument("--sigma0", type=float, default=100.0)
    ap.add_argument("--amp", type=float, default=80.0)
    ap.add_argument("--r0", type=float, default=0.08)

    # CalculiX params
    ap.add_argument("--ccx-exe", default="ccx")
    ap.add_argument(
        "--ccx-job",
        default="job",
        help="Nombre del job (sin extensión), ej: job -> job.inp",
    )
    ap.add_argument(
        "--ccx-workdir",
        default="",
        help="Workdir de ccx. Si no se da: runs/<case>/ccx/<tag>/",
    )
    ap.add_argument("--gmsh-exe", default="gmsh", help="Ejecutable de gmsh para autogenerar mesh.inp")
    ap.add_argument(
        "--ccx-run",
        action="store_true",
        help="Si se activa, ejecuta ccx antes de leer sigma_vm.csv.",
    )

    ap.add_argument(
        "--ccx-autogen-inp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Si faltan mesh.inp/job.inp, intenta generarlos automáticamente.",
    )
    ap.add_argument("--mat-name", default="MAT1")
    ap.add_argument("--mat-e", type=float, default=210000.0)
    ap.add_argument("--mat-nu", type=float, default=0.30)
    ap.add_argument("--face-tol", type=float, default=1e-6)
    ap.add_argument("--fix-axis", choices=["x", "y", "z"], default="z")
    ap.add_argument("--fix-side", choices=["min", "max"], default="min")
    ap.add_argument("--load-axis", choices=["x", "y", "z"], default="z")
    ap.add_argument("--load-side", choices=["min", "max"], default="max")
    ap.add_argument("--load-f", type=float, default=-1000.0)

    ap.add_argument("--cgx-exe", default="cgx")
    ap.add_argument(
        "--cgx-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Si falta sigma_vm.csv tras ccx, intenta extraerlo automáticamente con cgx.",
    )

    args = ap.parse_args()
    runs_dir = Path(args.runs_dir)

    ensure_case_dirs(args.case, runs_dir)

    geom = pd.read_parquet(geometry_parquet(args.case, args.geom_tag, runs_dir)).copy()
    required = {"elem_id", "cx", "cy", "cz"}
    missing = [c for c in required if c not in geom.columns]
    if missing:
        raise ValueError(f"Faltan columnas {missing} en geometría")

    if args.backend == "fallback":
        sigma_df = _fallback_sigma(
            geom=geom,
            tag=args.tag,
            tipx=args.tipx,
            tipy=args.tipy,
            tipz=args.tipz,
            sigma0=args.sigma0,
            amp=args.amp,
            r0=args.r0,
        )
        note = f"Nota: se usó fallback gaussiano para tag={args.tag}."

    else:  # calculix
        workdir = (
            _normalize_cli_path(args.ccx_workdir)
            if args.ccx_workdir
            else _default_ccx_workdir(args.case, runs_dir, args.tag)
        )
        workdir.mkdir(parents=True, exist_ok=True)

        mesh_inp = workdir / "mesh.inp"
        inp = workdir / f"{args.ccx_job}.inp"

        if args.ccx_run and args.ccx_autogen_inp:
            if not mesh_inp.exists():
                msh_path = _guess_msh_path(args.case, runs_dir, args.tag)
                _export_mesh_inp_from_msh(
                    gmsh_exe=args.gmsh_exe,
                    msh_path=msh_path,
                    out_inp=mesh_inp,
                )

            if not inp.exists():
                nodes = _read_nodes_from_inp(mesh_inp)
                elems = _read_elements_from_inp(mesh_inp)
                inp = _autogen_job_inp(
                    workdir=workdir,
                    ccx_job=args.ccx_job,
                    case=args.case,
                    tag=args.tag,
                    mesh_inp_name="mesh.inp",
                    nodes=nodes,
                    elems=elems,
                    mat_name=args.mat_name,
                    mat_e=args.mat_e,
                    mat_nu=args.mat_nu,
                    fix_axis=args.fix_axis,
                    fix_side=args.fix_side,
                    load_axis=args.load_axis,
                    load_side=args.load_side,
                    face_tol=args.face_tol,
                    load_f_total=args.load_f,
                )
                print(f"Info: creado automáticamente {inp}")

        if args.ccx_run:
            if not inp.exists():
                raise FileNotFoundError(
                    f"Falta INP para CalculiX: {inp}. "
                    "Coloca ese archivo o usa --ccx-workdir/--ccx-job correctos, "
                    "o activa --ccx-autogen-inp."
                )
            run_ccx(args.ccx_exe, args.ccx_job, workdir)

        sigma_path = (
            _normalize_cli_path(args.sigma_file)
            if args.sigma_file
            else _default_sigma_csv(args.case, runs_dir, args.tag)
        )
        sigma_path = _normalize_cli_path(sigma_path)

        if args.ccx_run and not sigma_path.exists() and args.cgx_run:
            sigma_path.parent.mkdir(parents=True, exist_ok=True)
            print(
                f"Info: no existe {sigma_path}; intentando extraer con cgx desde "
                f"{workdir / (args.ccx_job + '.frd')}"
            )
            fbd = write_cgx_script(args.ccx_job, sigma_path)
            run_cgx(args.cgx_exe, workdir, fbd)

        ext_df = read_sigma_vm_table(sigma_path)

        sigma_df = geom[["elem_id"]].merge(ext_df, on="elem_id", how="left")
        nmiss = int(sigma_df["sigma_vm"].isna().sum())
        if nmiss > 0:
            raise RuntimeError(
                f"CalculiX externo no cubre {nmiss} elementos ({args.tag}). "
                "Revisa mapping elem_id solver <-> geometría."
            )
        note = f"Nota: se usó backend calculix desde {sigma_path}."

    out = sigma_vm_parquet(args.case, args.tag, runs_dir)
    sigma_df.to_parquet(out, index=False)

    print(f"OK: creado {out}")
    print(note)


if __name__ == "__main__":
    main()
