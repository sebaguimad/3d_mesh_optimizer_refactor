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
python -m mesh_app run --geo geo/placa_hole_3d.geo --case demo_01
```

Opciones principales:

- `--sigma-mode dummy|fem`
- `--gmsh-exe gmsh`
- `--python-exe python`
- `--runs-dir runs`
- `--fem-backend fallback|calculix`
- `--fem-sigma-coarse-file <csv/parquet>`
- `--fem-sigma-ref-file <csv/parquet>`
- `--[no-]fem-auto-fallback` (default: activo; usa fallback si faltan CSV FEM)

Salida esperada en `runs/<case>/gmsh/`:

- `coarse_3d.msh`
- `background_points_3d.pos`
- `adapt_3d.msh`
- `--fem-backend fallback|calculix`
- `--fem-sigma-coarse-file <csv/parquet>`
- `--fem-sigma-ref-file <csv/parquet>`


| Argumento      | Qué hace                                                                       |
| -------------- | ------------------------------------------------------------------------------ |
| `--geo`        | Archivo `.geo` de entrada (geometría).                                         |
| `--case`       | Nombre del caso → se crea carpeta `runs/<case>/`.                              |
| `--sigma-mode` | Fuente de sigma (`auto`, `dummy` o `fem`). 
| `--python-exe` | Python que se usará para correr los subprocesos `src3d` (debe ser tu `.venv`). |
| `--runs-dir`   | Carpeta base de salida (default: `runs`).                                      |



## Ejecución en un solo comando (recomendada)

Si quieres que todo corra de punta a punta con un único comando y que FEM sea opcional, usa `sigma-mode auto` (por defecto):

```powershell
.\.venv\Scripts\python.exe -m mesh_app run --geo geo/perno_slot_crosshole.geo --case perno_01 --python-exe .\.venv\Scripts\python.exe
```

Comportamiento de `auto`:
- Si existen ambos archivos FEM (`runs/<case>/ccx/coarse/sigma_vm.csv` y `runs/<case>/ccx/ref/sigma_vm.csv`, o los pasados por flags), usa CalculiX.
- Si no existen, usa `dummy` automáticamente y continúa el pipeline completo.


## Uso recomendado (PowerShell)

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

## FEM real (integración rápida con FEniCS)

El modo `--sigma-mode fem` acepta dos backends:

- `fallback` (sintético)
- `calculix` (consume una tabla FEM externa `elem_id,sigma_vm`; puede venir de CalculiX, ANSYS u otro solver)

Contrato de salida requerido por el pipeline:

- columnas: `elem_id`, `sigma_vm`
- se escriben en:
  - `runs/<case>/gmsh/sigma_vm_coarse_3d.parquet`
  - `runs/<case>/gmsh/sigma_vm_ref_3d.parquet`

### Opción A: dejar archivos por convención

Si dejas por convención los CSV de CalculiX en:

- `runs/<case>/ccx/coarse/sigma_vm.csv`
- `runs/<case>/ccx/ref/sigma_vm.csv`

puedes correr:

```powershell
.\.venv\Scripts\python.exe -m mesh_app run --geo geo/perno_slot_crosshole.geo --case perno_01 --sigma-mode fem --fem-backend calculix --python-exe .\.venv\Scripts\python.exe
```

### Opción B: pasar archivos explícitos

```powershell
.\.venv\Scripts\python.exe -m mesh_app run --geo geo/perno_slot_crosshole.geo --case perno_01 --sigma-mode fem --fem-backend calculix --fem-sigma-coarse-file ruta/al/coarse.csv --fem-sigma-ref-file ruta/al/ref.csv --python-exe .\.venv\Scripts\python.exe
```