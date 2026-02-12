"""Backward-compatible import shim.

Este módulo se mantiene para compatibilidad con imports antiguos.
La implementación canónica del pipeline vive en `mesh_app.pipeline.run_pipeline`.
"""

from mesh_app.pipeline.run_pipeline import run_end_to_end

__all__ = ["run_end_to_end"]
