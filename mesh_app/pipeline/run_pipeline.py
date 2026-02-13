# run_pipeline.py
from __future__ import annotations

from pathlib import Path

from mesh_app.config import RunConfig
from mesh_app.services.gmsh_service import GmshService
from mesh_app.services.pipeline_steps_service import PipelineStepsService
from src3d.fem.fenics_runner import default_sigma_file

def _build_temp_adapt_geo(geo_abs: Path, bg_local_name: str = "background_points_3d.pos") -> str:
    return f'''SetFactory("OpenCASCADE");

Merge "{geo_abs.as_posix()}";
Merge "{bg_local_name}";

Field[1] = PostView;
Field[1].ViewIndex = 0;
Background Field = 1;

Mesh.MeshSizeExtendFromBoundary = 0;
Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;

Mesh.Algorithm3D = 4;
Mesh.Optimize = 1;
Mesh.OptimizeNetgen = 1;
'''

def _normalize_cli_path(path: Path | str) -> Path:
    clean = str(path).strip().strip('"').strip("'")
    return Path(clean).expanduser()


def _resolve_fem_sigma_inputs(cfg: RunConfig) -> tuple[Path, Path]:
    coarse_raw = cfg.fem_sigma_coarse_file or default_sigma_file(cfg.case, cfg.runs_dir, "coarse")
    ref_raw = cfg.fem_sigma_ref_file or default_sigma_file(cfg.case, cfg.runs_dir, "ref")

    coarse = _normalize_cli_path(coarse_raw)
    ref = _normalize_cli_path(ref_raw)

    missing = [p for p in (coarse, ref) if not p.exists()]
    if missing:
        missing_txt = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(
            "Faltan archivos FEM para backend fenics_csv antes de iniciar el pipeline: "
            f"{missing_txt}. "
            "Exporta fenics_sigma_vm_coarse/ref.csv o pasa --fem-sigma-coarse-file y --fem-sigma-ref-file con rutas reales."
        )
    return coarse, ref

def run_end_to_end(
    cfg: RunConfig,
    tipx: float = 0.25,
    tipy: float = 0.50,
    tipz: float = 0.005,
) -> None:
    cfg.validate()
    cfg.ensure_dirs()

    if cfg.sigma_mode == "fem" and cfg.fem_backend == "fenics_csv":
        fem_coarse, fem_ref = _resolve_fem_sigma_inputs(cfg)
        cfg = RunConfig(
            case=cfg.case,
            geo=cfg.geo,
            runs_dir=cfg.runs_dir,
            gmsh_exe=cfg.gmsh_exe,
            python_exe=cfg.python_exe,
            sigma_mode=cfg.sigma_mode,
            fem_backend=cfg.fem_backend,
            fem_sigma_coarse_file=fem_coarse,
            fem_sigma_ref_file=fem_ref,
        )



    gmsh = GmshService(cfg.gmsh_exe)
    steps = PipelineStepsService(cfg.python_exe, runs_dir=cfg.runs_dir)

    print("=== PIPELINE 3D START ===")
    print(f"case      : {cfg.case}")
    print(f"geo       : {cfg.geo}")
    print(f"sigma_mode: {cfg.sigma_mode}")

    # 1) coarse
    gmsh.mesh_coarse(cfg.geo, cfg.coarse_msh())

    # 2) features
    steps.compute_geometry(cfg.case, cfg.coarse_msh())

    # 3) sigma source
    if cfg.sigma_mode == "dummy":
        steps.compute_sigma_dummy(cfg.case, tipx, tipy, tipz)
    else:
        steps.compute_sigma_fem(
            cfg.case,
            backend=cfg.fem_backend,
            sigma_coarse_file=cfg.fem_sigma_coarse_file,
            sigma_ref_file=cfg.fem_sigma_ref_file,
        )

    # 4) ML chain
    steps.compute_hstar(cfg.case)
    steps.train_model(cfg.case)
    steps.predict_hstar(cfg.case)
    steps.postprocess(cfg.case)
    steps.export_background(cfg.case)

    # 5) adaptive remesh from generated POS
    bg_path = cfg.background_pos()
    if not bg_path.exists():
        raise FileNotFoundError(f"No existe background .pos: {bg_path}")

    temp_geo = cfg.gmsh_dir() / "temp_adapt_3d.geo"
    temp_geo.write_text(_build_temp_adapt_geo(cfg.geo.resolve()), encoding="utf-8")

    try:
        gmsh.mesh_adapt_with_pos(temp_geo=temp_geo, workdir=cfg.gmsh_dir(), out_name=cfg.adapt_name)
    finally:
        temp_geo.unlink(missing_ok=True)

    steps.compute_geometry(cfg.case, cfg.adapt_msh(), tag="adapt")

    print("\n✅ DONE")
    print(f"Coarse: {cfg.coarse_msh()}")
    print(f"Adapt : {cfg.adapt_msh()}")
    print(f"BG POS: {cfg.background_pos()}")
