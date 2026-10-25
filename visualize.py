#!/usr/bin/env python3
"""
Visualización de la simulación de colisión planetaria
Usando matplotlib y swiftsimio - guarda imágenes en lugar de mostrar ventana
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from planetary_utils import (
    EARTH_RADIUS_M,
    color_values,
    discover_snapshots,
    load_snapshot,
    project_positions,
    sample_indices,
    snapshot_time_hours,
    subset_snapshot,
)

SNAPSHOT_DIR = "simulation_output"
LEGACY_SNAPSHOT_DIR = "simulation/snapshots"
OUTPUT_DIR = "visualization_output"
FIGURE_SIZE = (12, 10)
PARTICLE_SIZE = 0.4


def resolve_snapshot_dir(snapshot_dir=None):
    if snapshot_dir is not None:
        return Path(snapshot_dir)

    default_dir = Path(SNAPSHOT_DIR)
    if default_dir.exists():
        return default_dir
    return Path(LEGACY_SNAPSHOT_DIR)


def load_latest_snapshot(snapshot_dir=None):
    snapshots = discover_snapshots(resolve_snapshot_dir(snapshot_dir))
    if not snapshots:
        return None
    return snapshots[-1]


def visualize_snapshot(
    snapshot_path,
    output_path=None,
    projection="xy",
    color_by="material",
    max_particles=25000,
    dpi=140,
):
    snapshot = load_snapshot(snapshot_path)
    indices = sample_indices(len(snapshot["position_m"]), max_particles)
    snapshot = subset_snapshot(snapshot, indices)
    x_m, y_m, xlabel, ylabel = project_positions(snapshot["position_m"], projection)
    colors, color_label = color_values(snapshot, color_by)
    cmap = "tab20" if color_by == "material" else "viridis"

    fig = plt.figure(figsize=FIGURE_SIZE)
    ax = fig.add_subplot(111)
    scatter = ax.scatter(
        x_m / EARTH_RADIUS_M,
        y_m / EARTH_RADIUS_M,
        c=colors,
        cmap=cmap,
        s=PARTICLE_SIZE,
        alpha=0.75,
        linewidths=0,
        rasterized=True,
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_aspect("equal")
    time_hours = snapshot_time_hours(snapshot)
    ax.set_title(f"Colisión Planetaria - {Path(snapshot_path).name} - t={time_hours:.2f} h")
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label(color_label)

    x_re = x_m / EARTH_RADIUS_M
    y_re = y_m / EARTH_RADIUS_M
    max_range = max(np.max(np.abs(x_re)), np.max(np.abs(y_re)))
    if not np.isfinite(max_range) or max_range <= 0.0:
        max_range = 1.0
    ax.set_xlim(-1.05 * max_range, 1.05 * max_range)
    ax.set_ylim(-1.05 * max_range, 1.05 * max_range)
    plt.tight_layout()

    if output_path is None:
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"vis_{Path(snapshot_path).stem}.png"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Imagen guardada: {output_path}")
    return output_path


def visualize_all_snapshots(snapshot_dir=None, output_dir=OUTPUT_DIR, projection="xy", color_by="material", max_particles=25000, dpi=140):
    snapshots = discover_snapshots(resolve_snapshot_dir(snapshot_dir))
    if not snapshots:
        print("No se encontraron snapshots")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Encontrados {len(snapshots)} snapshots")
    print("Generando visualizaciones...")

    for index, snapshot in enumerate(snapshots, start=1):
        print(f"[{index}/{len(snapshots)}] Visualizando {snapshot.name}")
        visualize_snapshot(
            snapshot,
            output_path=output_dir / f"vis_{snapshot.stem}.png",
            projection=projection,
            color_by=color_by,
            max_particles=max_particles,
            dpi=dpi,
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualizar simulación de colisión planetaria")
    parser.add_argument("--all", action="store_true", help="Visualizar todos los snapshots")
    parser.add_argument("--snapshot", type=str, help="Ruta al snapshot específico")
    parser.add_argument("--snapshot-dir", type=str, default=None, help="Directorio con snapshots")
    parser.add_argument("--output", type=str, default=None, help="Archivo PNG de salida para un snapshot")
    parser.add_argument("--output-dir", type=str, default=OUTPUT_DIR, help="Directorio de salida para --all")
    parser.add_argument("--projection", choices=["xy", "xz", "yz"], default="xy", help="Plano de proyección")
    parser.add_argument("--color-by", choices=["material", "speed", "mass", "density", "radius"], default="material", help="Magnitud usada para colorear")
    parser.add_argument("--max-particles", type=int, default=25000, help="Máximo de partículas a dibujar")
    parser.add_argument("--dpi", type=int, default=140, help="Resolución de salida")

    args = parser.parse_args()

    if args.all:
        visualize_all_snapshots(
            snapshot_dir=args.snapshot_dir,
            output_dir=args.output_dir,
            projection=args.projection,
            color_by=args.color_by,
            max_particles=args.max_particles,
            dpi=args.dpi,
        )
    elif args.snapshot:
        visualize_snapshot(
            args.snapshot,
            output_path=args.output,
            projection=args.projection,
            color_by=args.color_by,
            max_particles=args.max_particles,
            dpi=args.dpi,
        )
    else:
        snapshot = load_latest_snapshot(args.snapshot_dir)
        if snapshot:
            visualize_snapshot(
                snapshot,
                output_path=args.output,
                projection=args.projection,
                color_by=args.color_by,
                max_particles=args.max_particles,
                dpi=args.dpi,
            )
        else:
            print("No se encontraron snapshots. Ejecuta SWIFT primero.")
