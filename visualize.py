#!/usr/bin/env python3
"""
Visualización de la simulación de colisión planetaria
Usando matplotlib y swiftsimio - guarda imágenes en lugar de mostrar ventana
"""

import sys
sys.path.insert(0, '/home/ismaelmartin/.codex/astro-emulator/venv/lib/python3.12/site-packages')

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Usar backend no-interactivo
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import swiftsimio
import glob
import os

# Configuración de la visualización
SNAPSHOT_DIR = "simulation/snapshots"
OUTPUT_DIR = "visualization_output"
FIGURE_SIZE = (12, 10)
PARTICLE_SIZE = 0.5
VIEW_ANGLE_ELEV = 30
VIEW_ANGLE_AZIM = 45

def load_latest_snapshot():
    """Cargar el snapshot más reciente del directorio de snapshots"""
    if not os.path.exists(SNAPSHOT_DIR):
        print(f"Directorio de snapshots no encontrado: {SNAPSHOT_DIR}")
        return None
    
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "impact_*.hdf5")))
    if not snapshots:
        print("No se encontraron snapshots")
        return None
    
    return snapshots[-1]  # Retornar el más reciente

def visualize_snapshot(snapshot_path, output_path=None):
    """Visualizar un snapshot específico y guardar como imagen"""
    try:
        data = swiftsimio.load(snapshot_path)
        pos = data.gas.coordinates
        rho = data.gas.densities
        
        # Crear figura 2D más rápida
        fig = plt.figure(figsize=FIGURE_SIZE)
        ax = fig.add_subplot(111)
        
        # Proyección 2D (plano XY)
        scatter = ax.scatter(
            pos[:, 0] / 1e6,
            pos[:, 1] / 1e6,
            c=rho,
            cmap='viridis',
            s=PARTICLE_SIZE,
            alpha=0.6
        )
        
        # Configurar ejes
        ax.set_xlabel('X (R_earth)')
        ax.set_ylabel('Y (R_earth)')
        ax.set_title(f'Colisión Planetaria - {os.path.basename(snapshot_path)}')
        ax.set_aspect('equal')
        
        # Añadir barra de color para densidad
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Densidad (kg/m³)')
        
        # Ajustar límites para centrar en la colisión
        max_range = np.max(np.abs(pos[:, :2] / 1e6)) * 1.1
        ax.set_xlim(-max_range, max_range)
        ax.set_ylim(-max_range, max_range)
        
        plt.tight_layout()
        
        # Guardar imagen
        if output_path is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(OUTPUT_DIR, f"vis_{os.path.basename(snapshot_path)}.png")
        
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        print(f"Imagen guardada: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error al visualizar snapshot: {e}")
        return None

def visualize_all_snapshots():
    """Visualizar todos los snapshots disponibles"""
    if not os.path.exists(SNAPSHOT_DIR):
        print(f"Directorio de snapshots no encontrado: {SNAPSHOT_DIR}")
        return
    
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "impact_*.hdf5")))
    if not snapshots:
        print("No se encontraron snapshots")
        return
    
    print(f"Encontrados {len(snapshots)} snapshots")
    print("Generando visualizaciones...")
    
    for i, snapshot in enumerate(snapshots):
        print(f"[{i+1}/{len(snapshots)}] Visualizando {os.path.basename(snapshot)}")
        visualize_snapshot(snapshot)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualizar simulación de colisión planetaria')
    parser.add_argument('--all', action='store_true', help='Visualizar todos los snapshots')
    parser.add_argument('--snapshot', type=str, help='Ruta al snapshot específico')
    
    args = parser.parse_args()
    
    if args.all:
        visualize_all_snapshots()
    elif args.snapshot:
        visualize_snapshot(args.snapshot)
    else:
        # Intentar cargar el último snapshot
        snapshot = load_latest_snapshot()
        if snapshot:
            visualize_snapshot(snapshot)
        else:
            print("No se encontraron snapshots. Ejecuta SWIFT primero.")
