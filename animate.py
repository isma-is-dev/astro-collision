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

def create_animation(snapshots, output_file=OUTPUT_FILE, skip=1):
    """Crear animación de los snapshots"""
    # Aplicar skip para reducir número de frames
    if skip > 1:
        snapshots = snapshots[::skip]
        print(f"Usando {len(snapshots)} frames (saltando cada {skip} snapshots)")
    else:
        print(f"Creando animación con {len(snapshots)} snapshots...")
    
    # Pre-cargar todos los datos en memoria para mayor velocidad
    print("Pre-cargando datos...")
    all_data = []
    for snapshot_path in snapshots:
        data = swiftsimio.load(snapshot_path)
        all_data.append({
            'pos': data.gas.coordinates / 1e6,  # Convertir a R_earth
            'rho': data.gas.densities
        })
    print("Datos pre-cargados")
    
    # Configurar figura 3D
    fig = plt.figure(figsize=FIGURE_SIZE)
    ax = fig.add_subplot(111, projection='3d')
    
    # Configurar ejes con el primer snapshot
    pos0 = all_data[0]['pos']
    max_range = np.max(np.abs(pos0)) * 1.5
    
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
        try:
            data = all_data[frame]
            pos = data['pos']
            rho = data['rho']
            
            # Actualizar posiciones y colores (3D)
            scatter._offsets3d = (pos[:, 0], pos[:, 1], pos[:, 2])
            scatter.set_array(rho)
            
            # Actualizar título con número de frame
            ax.set_title(f'Colisión Planetaria - Frame {frame}/{len(all_data)-1}')
            
            return scatter,
        except Exception as e:
            print(f"Error en frame {frame}: {e}")
            return scatter,
    
    # Crear animación
    anim = animation.FuncAnimation(
        fig,
        update,
        frames=len(all_data),
        interval=1000/FPS,
        blit=False
    )
    
    # Guardar animación
    print(f"Guardando animación en {output_file}...")
    anim.save(output_file, writer='pillow', fps=FPS, dpi=80)
    plt.close(fig)
    
    print(f"Animación guardada: {output_file}")
    return output_file

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Crear animación de simulación de colisión planetaria')
    parser.add_argument('--output', type=str, default=OUTPUT_FILE, help='Archivo de salida (GIF)')
    parser.add_argument('--fps', type=int, default=FPS, help='Frames por segundo')
    parser.add_argument('--skip', type=int, default=1, help='Saltar N snapshots (reduce número de frames)')
    
    args = parser.parse_args()
    
    snapshots = load_snapshots()
    if snapshots:
        create_animation(snapshots, args.output, skip=args.skip)
    else:
        print("No se encontraron snapshots. Ejecuta SWIFT primero.")
