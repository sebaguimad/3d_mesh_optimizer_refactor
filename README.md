## Instalación

```bash
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Pipeline modular (`mesh_app`)

Se añadió una CLI modular que conserva el flujo original de `scripts/run_case_3d.ps1` pero desde Python:

```bash
python -m mesh_app run --geo geo/placa_hole_3d.geo --case demo_01 --sigma-mode dummy
```

Opciones principales:

- `--sigma-mode dummy|fem`
- `--gmsh-exe gmsh`
- `--python-exe python`
- `--runs-dir runs`

Salida esperada en `runs/<case>/gmsh/`:

- `coarse_3d.msh`
- `background_points_3d.pos`
- `adapt_3d.msh`


| Argumento      | Qué hace                                                                       |
| -------------- | ------------------------------------------------------------------------------ |
| `--geo`        | Archivo `.geo` de entrada (geometría).                                         |
| `--case`       | Nombre del caso → se crea carpeta `runs/<case>/`.                              |
| `--sigma-mode` | Fuente de sigma (`dummy` o `fem`).                                             |
| `--python-exe` | Python que se usará para correr los subprocesos `src3d` (debe ser tu `.venv`). |
| `--runs-dir`   | Carpeta base de salida (default: `runs`).                                      |


## Flujo completo: cómo funciona

1. Genera una malla coarse con Gmsh.
2. Calcula la geometría de elementos (centroide, volumen, h_cbrtV) y la guarda en Parquet.
3. Genera sigma (dummy o FEM), entrena un modelo y predice tamaños objetivo.
4. Exporta un *background field* (`background_points_3d.pos`) para el remallado.
5. Genera la malla adaptativa con Gmsh.
6. Calcula la geometría de elementos para la malla adaptativa (Parquet con sufijo `_adapt`).

## Uso recomendado (PowerShell)

### 1) Pipeline completo (coarse + adapt + parquet)

```powershell
.\.venv\Scripts\python.exe -m mesh_app run --geo geo/placa_hole_3d.geo --case demo_01 --sigma-mode dummy --python-exe .\.venv\Scripts\python.exe
```

### 2) Histogramas de tamaños (coarse vs adapt)

`plot-hist` grafica histogramas de `h_cbrtV` usando los parquets de `runs/<case>/gmsh/`:

```powershell
.\.venv\Scripts\python.exe -m mesh_app plot-hist --case demo_01 --runs-dir runs --mode both --save-dir runs/demo_01/plots --no-show --python-exe .\.venv\Scripts\python.exe
```

### 3) Comparar mallas (opcional)

```powershell
.\.venv\Scripts\python.exe -m mesh_app compare-meshes --coarse runs/demo_01/gmsh/coarse_3d.msh --adapt runs/demo_01/gmsh/adapt_3d.msh --outdir mesh_compare_out --python-exe .\.venv\Scripts\python.exe
```