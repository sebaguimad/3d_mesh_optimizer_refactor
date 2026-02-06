from __future__ import annotations

from pathlib import Path

from mesh_app.utils.subprocess_utils import run_cmd


class GmshService:
    def __init__(self, gmsh_exe: str = "gmsh"):
        self.gmsh_exe = gmsh_exe

    def mesh_coarse(self, geo: Path, out_msh: Path) -> None:
        out_msh.parent.mkdir(parents=True, exist_ok=True)
        run_cmd([
            self.gmsh_exe,
            str(geo),
            "-3",
            "-format",
            "msh2",
            "-o",
            str(out_msh),
        ])

    def mesh_adapt_with_pos(self, temp_geo: Path, workdir: Path, out_name: str = "adapt_3d.msh") -> None:
        run_cmd(
            [
                self.gmsh_exe,
                str(temp_geo.name),
                "-3",
                "-format",
                "msh2",
                "-o",
                out_name,
            ],
            cwd=workdir,
        )