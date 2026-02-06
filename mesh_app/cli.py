from __future__ import annotations

import argparse
from pathlib import Path

from mesh_app.config import RunConfig
from mesh_app.pipeline.run_pipeline import run_end_to_end


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mesh_app", description="CLI modular para optimización de malla 3D")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Ejecuta pipeline end-to-end")
    run.add_argument("--geo", required=True, type=Path, help="Ruta al .geo")
    run.add_argument("--case", required=True, help="Nombre del caso (runs/<case>)")
    run.add_argument("--sigma-mode", default="dummy", choices=["dummy", "fem"])
    run.add_argument("--gmsh-exe", default="gmsh")
    run.add_argument("--python-exe", default="python")
    run.add_argument("--runs-dir", type=Path, default=Path("runs"))
    run.add_argument("--tipx", type=float, default=0.25)
    run.add_argument("--tipy", type=float, default=0.50)
    run.add_argument("--tipz", type=float, default=0.005)

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
        )
        run_end_to_end(cfg, tipx=args.tipx, tipy=args.tipy, tipz=args.tipz)


if __name__ == "__main__":
    main()