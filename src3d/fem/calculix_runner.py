# src3d/fem/calculix_runner.py
from __future__ import annotations

import subprocess
from pathlib import Path


def run_ccx(ccx_exe: str, job_name: str, workdir: Path) -> tuple[Path, Path]:
    """
    Ejecuta CalculiX: ccx -i <job_name> en workdir
    Espera outputs estándar: <job>.frd y <job>.dat
    """
    workdir.mkdir(parents=True, exist_ok=True)

    cmd = [ccx_exe, "-i", job_name]
    print(f"[cmd] {' '.join(cmd)} (cwd={workdir})")
    proc = subprocess.run(cmd, cwd=str(workdir), check=False)

    if proc.returncode != 0:
        raise RuntimeError(f"CalculiX falló ({proc.returncode}) con CMD: {' '.join(cmd)}")

    frd = workdir / f"{job_name}.frd"
    dat = workdir / f"{job_name}.dat"
    if not frd.exists():
        raise FileNotFoundError(f"No se generó FRD: {frd}")

    return frd, dat
