# pipeline_steps_service.py
from __future__ import annotations

from pathlib import Path

from mesh_app.utils.subprocess_utils import run_cmd


class PipelineStepsService:
    def __init__(self, python_exe: str = "python"):
        self.python_exe = python_exe

    def compute_geometry(self, case: str, msh: Path) -> None:
        run_cmd([
            self.python_exe,
            "-m",
            "src3d.compute_element_geometry_3d",
            "--case",
            case,
            "--msh",
            str(msh),
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
        ])

    def compute_sigma_fem(self, case: str, msh: Path) -> None:
        # Requiere que exista el módulo src3d.solve_and_extract_sigma_vm_3d en el entorno del usuario.
        for tag in ("coarse", "ref"):
            run_cmd([
                self.python_exe,
                "-m",
                "src3d.solve_and_extract_sigma_vm_3d",
                "--case",
                case,
                "--mesh",
                str(msh),
                "--tag",
                tag,
            ])

    def compute_hstar(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.compute_hstar_3d", "--case", case])

    def train_model(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.train_ml_hstar_3d", "--case", case])

    def predict_hstar(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.predict_hstar_3d", "--case", case])

    def postprocess(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.postprocess_h_pred_3d", "--case", case])

    def export_background(self, case: str) -> None:
        run_cmd([self.python_exe, "-m", "src3d.export_background_points_3d", "--case", case])