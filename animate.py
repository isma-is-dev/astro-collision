#!/usr/bin/env python3
"""
Animación de la simulación de colisión planetaria
Genera un GIF animado o MP4 de los snapshots de SWIFT
"""

import sys
sys.path.insert(0, '/home/ismaelmartin/.codex/astro-emulator/venv/lib/python3.12/site-packages')

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Usar backend no-interactivo
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
import swiftsimio
import glob
import os

# Configuración
SNAPSHOT_DIR = "simulation/snapshots"
OUTPUT_FILE = "collision_animation.gif"
FIGURE_SIZE = (10, 8)
PARTICLE_SIZE = 0.5
VIEW_ANGLE_ELEV = 30
VIEW_ANGLE_AZIM = 45
FPS = 10

def load_snapshots():
    """Cargar todos los snapshots disponibles"""
    if not os.path.exists(SNAPSHOT_DIR):
        print(f"Directorio de snapshots no encontrado: {SNAPSHOT_DIR}")
        return []
    
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "impact_*.hdf5")))
    if not snapshots:
        print("No se encontraron snapshots")
        return []
    
    return snapshots

def create_animation(snapshots, output_file=OUTPUT_FILE):
    """Crear animación de los snapshots"""
    print(f"Creando animación con {len(snapshots)} snapshots...")
    
    # Configurar figura
    fig = plt.figure(figsize=FIGURE_SIZE)
    ax = fig.add_subplot(111, projection='3d')
    
    # Cargar primer snapshot para configurar ejes
    data0 = swiftsimio.load(snapshots[0])
    pos0 = data0.gas.coordinates
    max_range = np.max(np.abs(pos0 / 1e6)) * 1.5
    
    ax.set_xlim(-max_range, max_range)
    ax.set_ylim(-max_range, max_range)
    ax.set_zlim(-max_range, max_range)
    ax.set_xlabel('X (R_earth)')
    ax.set_ylabel('Y (R_earth)')
    ax.set_zlabel('Z (R_earth)')
    ax.set_title('Colisión Planetaria')
    
    # Inicializar scatter plot vacío
    scatter = ax.scatter([], [], [], c=[], cmap='viridis', s=PARTICLE_SIZE, alpha=0.6)
    
    def update(frame):
        """Función de actualización para la animación"""
        snapshot_path = snapshots[frame]
        try:
            data = swiftsimio.load(snapshot_path)
            pos = data.gas.coordinates
            rho = data.gas.densities
            
            # Actualizar posiciones y colores
            scatter._offsets3d = (
                pos[:, 0] / 1e6,
                pos[:, 1] / 1e6,
                pos[:, 2] / 1e6
            )
            scatter.set_array(rho)
            
            # Actualizar título con número de frame
            ax.set_title(f'Colisión Planetaria - Frame {frame}/{len(snapshots)-1}')
            
            return scatter,
        except Exception as e:
            print(f"Error en frame {frame}: {e}")
            return scatter,
    
    # Crear animación
    anim = animation.FuncAnimation(
        fig, 
        update, 
        frames=len(snapshots),
        interval=1000/FPS,
        blit=False
    )
    
    # Guardar animación
    print(f"Guardando animación en {output_file}...")
    anim.save(output_file, writer='pillow', fps=FPS)
    plt.close(fig)
    
    print(f"Animación guardada: {output_file}")
    return output_file

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Crear animación de simulación de colisión planetaria')
    parser.add_argument('--output', type=str, default=OUTPUT_FILE, help='Archivo de salida (GIF)')
    parser.add_argument('--fps', type=int, default=FPS, help='Frames por segundo')
    
    args = parser.parse_args()
    
    snapshots = load_snapshots()
    if snapshots:
        create_animation(snapshots, args.output)
    else:
        print("No se encontraron snapshots. Ejecuta SWIFT primero.")
