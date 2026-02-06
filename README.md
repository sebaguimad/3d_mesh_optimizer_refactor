 ## Instalación
 
 ```bash
 python -m venv .venv
 
 # Linux/Mac
 source .venv/bin/activate
 
 # Windows
 .\.venv\Scripts\Activate.ps1
 
 pip install -r requirements.txt

## Pipeline modular (`mesh_app`)

Se añadió una CLI modular que conserva el flujo original de `scripts/run_case_3d.ps1` pero desde Python:

```bash
+python -m mesh_app run --geo geo/placa_hole_3d.geo --case demo_01 --sigma-mode dummy
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
