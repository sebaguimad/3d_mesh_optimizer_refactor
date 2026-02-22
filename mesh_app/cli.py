# mesh_app/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from mesh_app.config import RunConfig
from mesh_app.pipeline.run_pipeline import run_end_to_end
from mesh_app.utils.subprocess_utils import run_cmd


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mesh_app",
        description="CLI modular para optimización de malla 3D",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # -------------------------
    # run
    # -------------------------
    run = sub.add_parser("run", help="Ejecuta pipeline end-to-end")
    run.add_argument("--geo", required=True, type=Path, help="Ruta al .geo")
    run.add_argument("--case", required=True, help="Nombre del caso (runs/<case>)")
    run.add_argument("--sigma-mode", default="auto", choices=["auto", "dummy", "fem"], help="Fuente de sigma: auto (usa FEM si está disponible, si no dummy), dummy o fem")
    run.add_argument("--gmsh-exe", default="gmsh")
    run.add_argument("--python-exe", default="python")
    run.add_argument("--runs-dir", type=Path, default=Path("runs"))
    run.add_argument("--tipx", type=float, default=0.25)
    run.add_argument("--tipy", type=float, default=0.50)
    run.add_argument("--tipz", type=float, default=0.005)
    run.add_argument("--fem-backend", default="fallback", choices=["fallback", "calculix"])
    run.add_argument("--fem-sigma-coarse-file", type=Path, default=None)
    run.add_argument("--fem-sigma-ref-file", type=Path, default=None)
    run.add_argument("--fem-ccx-run", action=argparse.BooleanOptionalAction, default=False, help="Ejecuta ccx para cada tag FEM (coarse/ref) antes de leer sigma_vm.")
    run.add_argument("--fem-ccx-exe", default="ccx")
    run.add_argument("--fem-ccx-job", default="job")
    run.add_argument("--fem-ccx-workdir-coarse", type=Path, default=None)
    run.add_argument("--fem-ccx-workdir-ref", type=Path, default=None)
    run.add_argument("--fem-cgx-exe", default="cgx")
    run.add_argument("--fem-cgx-run", action=argparse.BooleanOptionalAction, default=True)

    run.add_argument(
        "--fem-auto-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Si falta sigma CSV/Parquet en backend calculix, cae automáticamente "
            "a sigma sintético (fallback) para no abortar el pipeline."
        ),
    )

    # -------------------------
    # plot-hist
    # -------------------------
    plot = sub.add_parser("plot-hist", help="Grafica histogramas de h_cbrtV (coarse/adapt)")
    plot.add_argument("--case", required=True, help="Nombre del caso (runs/<case>)")
    plot.add_argument("--runs-dir", type=Path, default=Path("runs"))
    plot.add_argument("--coarse-tag", default="")
    plot.add_argument("--adapt-tag", default="adapt")
    plot.add_argument("--mode", choices=["separate", "overlay", "both"], default="separate")
    plot.add_argument("--bins", type=int, default=30)
    plot.add_argument("--col", default="h_cbrtV")
    plot.add_argument("--print-stats", action="store_true")
    plot.add_argument("--save-dir", default="", help="Si se entrega, guarda PNGs aquí (ej: runs/<case>/plots)")
    plot.add_argument("--no-show", action="store_true", help="No abrir ventanas, solo guardar")
    plot.add_argument("--python-exe", default="python")

    # -------------------------
    # compare-meshes
    # -------------------------
    compare = sub.add_parser("compare-meshes", help="Compara coarse vs adapt (msh)")
    compare.add_argument("--coarse", required=True, type=Path, help="Path a coarse_3d.msh")
    compare.add_argument("--adapt", required=True, type=Path, help="Path a adapt_3d.msh")
    compare.add_argument("--outdir", type=Path, default=Path("mesh_compare_out"))
    compare.add_argument("--python-exe", default="python")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        cfg = RunConfig(
            case=args.case,
            geo=args.geo,
            runs_dir=args.runs_dir,
            gmsh_exe=args.gmsh_exe,
            python_exe=args.python_exe,
            sigma_mode=args.sigma_mode,
            fem_backend=args.fem_backend,
            fem_sigma_coarse_file=args.fem_sigma_coarse_file,
            fem_sigma_ref_file=args.fem_sigma_ref_file,
            fem_ccx_run=args.fem_ccx_run,
            fem_ccx_exe=args.fem_ccx_exe,
            fem_ccx_job=args.fem_ccx_job,
            fem_ccx_workdir_coarse=args.fem_ccx_workdir_coarse,
            fem_ccx_workdir_ref=args.fem_ccx_workdir_ref,
            fem_cgx_exe=args.fem_cgx_exe,
            fem_cgx_run=args.fem_cgx_run,
        )
        run_end_to_end(
            cfg,
            tipx=args.tipx,
            tipy=args.tipy,
            tipz=args.tipz,
            fem_auto_fallback=args.fem_auto_fallback,
        )

    elif args.command == "plot-hist":
        cmd = [
            args.python_exe,
            "-m",
            "src3d.plot_hist_h3d",
            "--case",
            args.case,
            "--runs-dir",
            str(args.runs_dir),
            "--coarse_tag",
            args.coarse_tag,
            "--adapt_tag",
            args.adapt_tag,
            "--mode",
            args.mode,
            "--bins",
            str(args.bins),
            "--col",
            args.col,
        ]
        if args.print_stats:
            cmd.append("--print_stats")
        if args.save_dir:
            cmd.extend(["--save_dir", args.save_dir])
        if args.no_show:
            cmd.append("--no_show")

        run_cmd(cmd)

    elif args.command == "compare-meshes":
        run_cmd(
            [
                args.python_exe,
                str(Path("compare_meshes.py")),
                "--coarse",
                str(args.coarse),
                "--adapt",
                str(args.adapt),
                "--outdir",
                str(args.outdir),
            ]
        )


if __name__ == "__main__":
    main()
