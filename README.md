diff --git a/README.md b/README.md
index dd548a3bca246fd5b9af467c633fdbcb1336310b..f2e826d45e3a6851568ca29f4007936d4f913361 100644
--- a/README.md
+++ b/README.md
@@ -1,12 +1,33 @@
 ## Instalación
 
 ```bash
 python -m venv .venv
 
 # Linux/Mac
 source .venv/bin/activate
 
 # Windows
 .\.venv\Scripts\Activate.ps1
 
 pip install -r requirements.txt
+
+## Pipeline modular (`mesh_app`)
+
+Se añadió una CLI modular que conserva el flujo original de `scripts/run_case_3d.ps1` pero desde Python:
+
+```bash
+python -m mesh_app run --geo geo/placa_hole_3d.geo --case demo_01 --sigma-mode dummy
+```
+
+Opciones principales:
+
+- `--sigma-mode dummy|fem`
+- `--gmsh-exe gmsh`
+- `--python-exe python`
+- `--runs-dir runs`
+
+Salida esperada en `runs/<case>/gmsh/`:
+
+- `coarse_3d.msh`
+- `background_points_3d.pos`
+- `adapt_3d.msh`
