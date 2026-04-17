#!/usr/bin/env python3
"""
Animación de la simulación de colisión planetaria
Genera un GIF animado o MP4 de los snapshots de SWIFT
"""

import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import Normalize

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
OUTPUT_FILE = "collision_animation.gif"
FIGURE_SIZE = (10, 8)
PARTICLE_SIZE = 0.4
FPS = 10


def resolve_snapshot_dir(snapshot_dir=None):
    if snapshot_dir is not None:
        return Path(snapshot_dir)

    default_dir = Path(SNAPSHOT_DIR)
    if default_dir.exists():
        return default_dir
    return Path(LEGACY_SNAPSHOT_DIR)


def load_snapshots(snapshot_dir=None):
    return discover_snapshots(resolve_snapshot_dir(snapshot_dir))


def prepare_frame(snapshot_path, projection, color_by, indices):
    snapshot = load_snapshot(snapshot_path)
    if indices is not None:
        snapshot = subset_snapshot(snapshot, indices)

    x_m, y_m, xlabel, ylabel = project_positions(snapshot["position_m"], projection)
    colors, color_label = color_values(snapshot, color_by)
    return {
        "x": x_m / EARTH_RADIUS_M,
        "y": y_m / EARTH_RADIUS_M,
        "colors": colors,
        "xlabel": xlabel,
        "ylabel": ylabel,
        "color_label": color_label,
        "time_hours": snapshot_time_hours(snapshot),
    }


def estimate_limits(snapshot_paths, projection, color_by, indices):
    max_extent = 1.0
    color_min = None
    color_max = None

    for snapshot_path in snapshot_paths:
        frame = prepare_frame(snapshot_path, projection, color_by, indices)
        frame_extent = max(np.max(np.abs(frame["x"])), np.max(np.abs(frame["y"])))
        if np.isfinite(frame_extent) and frame_extent > 0.0:
            max_extent = max(max_extent, frame_extent)

        frame_color_min = float(np.min(frame["colors"]))
        frame_color_max = float(np.max(frame["colors"]))
        color_min = frame_color_min if color_min is None else min(color_min, frame_color_min)
        color_max = frame_color_max if color_max is None else max(color_max, frame_color_max)

    return max_extent, color_min, color_max


def create_animation(
    snapshots,
    output_file=OUTPUT_FILE,
    skip=1,
    projection="xy",
    color_by="material",
    max_particles=15000,
    fps=FPS,
    dpi=120,
):
    if skip > 1:
        snapshots = snapshots[::skip]
        print(f"Usando {len(snapshots)} frames (saltando cada {skip} snapshots)")
    else:
        print(f"Creando animación con {len(snapshots)} snapshots...")

    if not snapshots:
        raise ValueError("No snapshots provided")

    first_snapshot = load_snapshot(snapshots[0])
    indices = sample_indices(len(first_snapshot["position_m"]), max_particles)
    max_extent, color_min, color_max = estimate_limits(snapshots, projection, color_by, indices)
    first_frame = prepare_frame(snapshots[0], projection, color_by, indices)

    fig = plt.figure(figsize=FIGURE_SIZE)
    ax = fig.add_subplot(111)
    cmap = "tab20" if color_by == "material" else "viridis"
    norm = None if color_by == "material" else Normalize(vmin=color_min, vmax=color_max)
    scatter = ax.scatter(
        first_frame["x"],
        first_frame["y"],
        c=first_frame["colors"],
        cmap=cmap,
        norm=norm,
        s=PARTICLE_SIZE,
        alpha=0.75,
        linewidths=0,
        rasterized=True,
    )

    ax.set_xlim(-1.05 * max_extent, 1.05 * max_extent)
    ax.set_ylim(-1.05 * max_extent, 1.05 * max_extent)
    ax.set_aspect("equal")
    ax.set_xlabel(first_frame["xlabel"])
    ax.set_ylabel(first_frame["ylabel"])
    ax.set_title(f"Colisión Planetaria - t={first_frame['time_hours']:.2f} h")
    colorbar = plt.colorbar(scatter, ax=ax)
    colorbar.set_label(first_frame["color_label"])
    plt.tight_layout()

    def update(frame_index):
        frame = prepare_frame(snapshots[frame_index], projection, color_by, indices)
        offsets = np.column_stack([frame["x"], frame["y"]])
        scatter.set_offsets(offsets)
        scatter.set_array(np.asarray(frame["colors"]))
        ax.set_title(f"Colisión Planetaria - t={frame['time_hours']:.2f} h")
        return scatter,

    anim = animation.FuncAnimation(
        fig,
        update,
        frames=len(snapshots),
        interval=1000 / fps,
        blit=False,
    )

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    writer = "pillow" if output_file.suffix.lower() == ".gif" else "ffmpeg"
    print(f"Guardando animación en {output_file}...")
    anim.save(output_file, writer=writer, fps=fps, dpi=dpi)
    plt.close(fig)

    print(f"Animación guardada: {output_file}")
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crear animación de simulación de colisión planetaria")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="Archivo de salida (.gif o .mp4)")
    parser.add_argument("--fps", type=int, default=FPS, help="Frames por segundo")
    parser.add_argument("--skip", type=int, default=1, help="Saltar N snapshots")
    parser.add_argument("--snapshot-dir", type=str, default=None, help="Directorio con snapshots")
    parser.add_argument("--projection", choices=["xy", "xz", "yz"], default="xy", help="Plano de proyección")
    parser.add_argument("--color-by", choices=["material", "speed", "mass", "density", "radius"], default="material", help="Magnitud usada para colorear")
    parser.add_argument("--max-particles", type=int, default=15000, help="Máximo de partículas por frame")
    parser.add_argument("--dpi", type=int, default=120, help="Resolución de salida")

    args = parser.parse_args()

    snapshots = load_snapshots(args.snapshot_dir)
    if snapshots:
        create_animation(
            snapshots,
            output_file=args.output,
            skip=args.skip,
            projection=args.projection,
            color_by=args.color_by,
            max_particles=args.max_particles,
            fps=args.fps,
            dpi=args.dpi,
        )
    else:
        print("No se encontraron snapshots. Ejecuta SWIFT primero.")
