# plot_hist_h3d.py
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def read_geometry(case_dir: Path, tag: str | None) -> pd.DataFrame:
    tag = (tag or "").strip()
    fname = "element_geometry_3d.parquet" if tag == "" else f"element_geometry_3d_{tag}.parquet"
    path = case_dir / fname
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    return pd.read_parquet(path)


def common_bins(series_list: list[pd.Series], nbins: int) -> np.ndarray:
    all_vals = pd.concat(series_list, ignore_index=True)
    return np.histogram_bin_edges(all_vals.to_numpy(), bins=nbins)


def describe_h(df: pd.DataFrame, col: str = "h_cbrtV", name: str = "") -> None:
    s = df[col]
    print(
        f"{name:<7} n={len(s):<8} min={s.min():.6g}  max={s.max():.6g}  "
        f"mean={s.mean():.6g}  std={s.std():.6g}"
    )


def plot_hist_single(
    df: pd.DataFrame,
    title: str,
    bins: np.ndarray,
    col: str = "h_cbrtV",
    save_path: Path | None = None,
    show: bool = True,
) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 5))
    plt.hist(df[col], bins=bins, edgecolor="k")
    plt.xlabel("h = V^(1/3)")
    plt.ylabel("Número de tetraedros")
    plt.title(title)
    plt.tight_layout()
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=160)
    if show:
        plt.show()
    plt.close()


def plot_hist_overlay(
    coarse: pd.DataFrame,
    adapt: pd.DataFrame,
    title: str,
    bins: np.ndarray,
    col: str = "h_cbrtV",
    save_path: Path | None = None,
    show: bool = True,
) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 5))
    plt.hist(coarse[col], bins=bins, alpha=0.55, label="Coarse", edgecolor="k")
    plt.hist(adapt[col], bins=bins, alpha=0.55, label="Adapt", edgecolor="k")
    plt.xlabel("h = V^(1/3)")
    plt.ylabel("Número de tetraedros")
    plt.legend()
    plt.title(title)
    plt.tight_layout()
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=160)
    if show:
        plt.show()
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--coarse_tag", default="")
    ap.add_argument("--adapt_tag", default="adapt")
    ap.add_argument("--mode", choices=["separate", "overlay", "both"], default="separate")
    ap.add_argument("--bins", type=int, default=30)
    ap.add_argument("--col", default="h_cbrtV")
    ap.add_argument("--print_stats", action="store_true")
    ap.add_argument("--save_dir", default="", help="Si se entrega, guarda PNGs aquí (ej: runs/<case>/plots)")
    ap.add_argument("--no_show", action="store_true", help="No abrir ventanas, solo guardar (ideal para scripts)")
    args = ap.parse_args()

    case_dir = Path(args.runs_dir) / args.case
    coarse = read_geometry(case_dir, args.coarse_tag)
    adapt = read_geometry(case_dir, args.adapt_tag)

    if args.print_stats:
        describe_h(coarse, args.col, "coarse")
        describe_h(adapt, args.col, "adapt")

    bins = common_bins([coarse[args.col], adapt[args.col]], nbins=args.bins)

    save_dir = Path(args.save_dir) if args.save_dir else None
    show = not args.no_show

    if args.mode in ("separate", "both"):
        plot_hist_single(
            coarse,
            "Coarse: distribución de tamaños (3D)",
            bins,
            col=args.col,
            save_path=(save_dir / "hist_coarse.png") if save_dir else None,
            show=show,
        )
        plot_hist_single(
            adapt,
            "Adapt: distribución de tamaños (3D)",
            bins,
            col=args.col,
            save_path=(save_dir / "hist_adapt.png") if save_dir else None,
            show=show,
        )

    if args.mode in ("overlay", "both"):
        plot_hist_overlay(
            coarse,
            adapt,
            "Coarse vs Adapt: distribución de tamaños (3D)",
            bins,
            col=args.col,
            save_path=(save_dir / "hist_overlay.png") if save_dir else None,
            show=show,
        )


if __name__ == "__main__":
    main()