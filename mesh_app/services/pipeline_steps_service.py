# mesh_app/services/pipeline_steps_service.py
from __future__ import annotations

from pathlib import Path

from mesh_app.utils.subprocess_utils import run_cmd


def _normalize_cli_path(path: Path | str) -> Path:
    clean = str(path).strip().strip('"').strip("'")
    return Path(clean).expanduser()


class PipelineStepsService:
    def __init__(self, python_exe: str = "python", runs_dir: Path = Path("runs")):
        self.python_exe = python_exe
        self.runs_dir = runs_dir

    def _runs_dir_args(self) -> list[str]:
        return ["--runs-dir", str(self.runs_dir)]

    def compute_geometry(self, case: str, msh: Path, tag: str = "") -> None:
        run_cmd([
            self.python_exe, "-m", "src3d.compute_element_geometry_3d",
            "--case", case,
            "--msh", str(msh),
            "--tag", tag,
            *self._runs_dir_args(),
        ])

    def compute_sigma_dummy(self, case: str, tipx: float, tipy: float, tipz: float) -> None:
        run_cmd([
            self.python_exe, "-m", "src3d.make_dummy_sigma_vm_3d",
            "--case", case,
            "--tipx", str(tipx),
            "--tipy", str(tipy),
            "--tipz", str(tipz),
            *self._runs_dir_args(),
        ])

    def compute_sigma_fem(
        self,
        case: str,
        backend: str = "fallback",  # fallback | calculix
        sigma_coarse_file: Path | None = None,
        sigma_ref_file: Path | None = None,
        # calculix opcional:
        ccx_exe: str = "ccx",
        ccx_job: str = "job",
        ccx_workdir_coarse: Path | None = None,
        ccx_workdir_ref: Path | None = None,
        ccx_run: bool = False,
    ) -> None:
        sigma_files: dict[str, Path | None] = {"coarse": sigma_coarse_file, "ref": sigma_ref_file}
        workdirs: dict[str, Path | None] = {"coarse": ccx_workdir_coarse, "ref": ccx_workdir_ref}

        for tag in ("coarse", "ref"):
            cmd = [
                self.python_exe,
                "-m",
                "src3d.solve_and_extract_sigma_vm_3d",
                "--case", case,
                "--tag", tag,
                "--backend", backend,
                *self._runs_dir_args(),
            ]

            if backend == "calculix":
                cmd.extend(["--ccx-exe", ccx_exe, "--ccx-job", ccx_job])
                if ccx_run:
                    cmd.append("--ccx-run")

                wd = workdirs[tag]
                if wd is not None:
                    cmd.extend(["--ccx-workdir", str(_normalize_cli_path(wd))])

                sf = sigma_files[tag]
                if sf is not None:
                    p = _normalize_cli_path(sf)
                    if not p.exists():
                        raise FileNotFoundError(f"No existe sigma-file ({backend}) para tag={tag}: {p}")
                    cmd.extend(["--sigma-file", str(p)])

            # backend fallback: no necesita archivos

            run_cmd(cmd)

    def compute_hstar(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.compute_hstar_3d", "--case", case, *self._runs_dir_args()])

    def train_model(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.train_ml_hstar_3d", "--case", case, *self._runs_dir_args()])

    def predict_hstar(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.predict_hstar_3d", "--case", case, *self._runs_dir_args()])

    def postprocess(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.postprocess_h_pred_3d", "--case", case, *self._runs_dir_args()])

    def export_background(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.export_background_points_3d", "--case", case, *self._runs_dir_args()])
