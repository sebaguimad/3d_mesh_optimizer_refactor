# cgx_extract_sigma_vm.py
from __future__ import annotations

import subprocess
from pathlib import Path


def write_cgx_script(job_name: str, out_csv: Path) -> Path:
    """
    Escribe un .fbd batch para CGX.
    Convención: lee <job>.frd y exporta tabla a CSV.
    """
    fbd = out_csv.parent / "extract_sigma_vm.fbd"

    # Script BASE.
    # Dependiendo de tu versión cgx, podrías necesitar ajustar los comandos de export.
    content = f"""
read {job_name}.frd
# Seleccionar todos los elementos
seta all e all

# Activar resultados de stress (Von Mises)
# En algunas versiones se usa: ds 1 e
# o: plot fvm
# Mantengo un flujo simple y export a archivo

# Export "tabla" (si tu CGX no soporta send/print como aquí, lo ajustamos con tu output)
# --- BEGIN EXPORT (puede requerir ajuste) ---
sys wipeln {out_csv.name}
# La idea es escribir: elem_id,sigma_vm por línea.
# Algunas builds soportan 'send' / 'prnt' / 'asgn' distinto.
# --- END EXPORT ---

quit
"""
    fbd.write_text(content.strip() + "\n", encoding="utf-8")
    return fbd


def run_cgx(cgx_exe: str, workdir: Path, fbd: Path) -> None:
    cmd = [cgx_exe, "-b", fbd.name]
    proc = subprocess.run(
        cmd,
        cwd=str(workdir),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")

    if proc.returncode != 0:
        raise RuntimeError(f"CGX falló ({proc.returncode}) con CMD: {' '.join(cmd)}")
