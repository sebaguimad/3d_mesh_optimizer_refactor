# mesh_app/services/pipeline_steps_service.py
from __future__ import annotations

from pathlib import Path

from mesh_app.utils.subprocess_utils import run_cmd


class PipelineStepsService:
    def __init__(self, python_exe: str = "python", runs_dir: Path = Path("runs")):
        self.python_exe = python_exe
        self.runs_dir = runs_dir

    def _runs_dir_args(self) -> list[str]:
        return ["--runs-dir", str(self.runs_dir)]

    def compute_geometry(self, case: str, msh: Path, tag: str = "") -> None:
        run_cmd([
            self.python_exe,
            "-m",
            "src3d.compute_element_geometry_3d",
            "--case",
            case,
            "--msh",
            str(msh),
            "--tag",
            tag,
            *self._runs_dir_args(),
        ])

    def compute_sigma_dummy(self, case: str, tipx: float, tipy: float, tipz: float) -> None:
        run_cmd([
            self.python_exe,
            "-m",
            "src3d.make_dummy_sigma_vm_3d",
            "--case",
            case,
            "--tipx",
            str(tipx),
            "--tipy",
            str(tipy),
            "--tipz",
            str(tipz),
            *self._runs_dir_args(),
        ])

    def compute_sigma_fem(
        self,
        case: str,
        backend: str = "fallback",
        sigma_coarse_file: Path | None = None,
        sigma_ref_file: Path | None = None,
    ) -> None:
        sigma_files = {"coarse": sigma_coarse_file, "ref": sigma_ref_file}
        for tag in ("coarse", "ref"):
            cmd = [
                self.python_exe,
                "-m",
                "src3d.solve_and_extract_sigma_vm_3d",
                "--case",
                case,
                "--tag",
                tag,
                "--backend",
                backend,
                *self._runs_dir_args(),
            ]
            sigma_file = sigma_files[tag]
            if sigma_file is not None:
                cmd.extend(["--sigma-file", str(sigma_file)])
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
