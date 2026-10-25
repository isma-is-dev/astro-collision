#!/usr/bin/env python3
"""
Animación de la simulación de colisión planetaria usando vispy (GPU-accelerated)
"""

import sys
sys.path.insert(0, '/home/ismaelmartin/.codex/astro-emulator/venv/lib/python3.12/site-packages')

import numpy as np
from vispy import app, scene, io
import swiftsimio
import glob
import os

# Configuración
SNAPSHOT_DIR = "simulation/snapshots"
OUTPUT_FILE = "collision_animation_gpu.gif"
FIGURE_SIZE = (10, 8)
PARTICLE_SIZE = 2.0
FPS = 15

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

def create_animation_gpu(snapshots, output_file=OUTPUT_FILE):
    """Crear animación usando vispy (GPU-accelerated)"""
    print(f"Creando animación con {len(snapshots)} snapshots usando GPU...")
    
    # Pre-cargar todos los datos
    print("Pre-cargando datos...")
    all_data = []
    for snapshot_path in snapshots:
        data = swiftsimio.load(snapshot_path)
        all_data.append({
            'pos': data.gas.coordinates / 1e6,  # Convertir a R_earth
            'rho': data.gas.densities
        })
    print("Datos pre-cargados")
    
    # Configurar canvas vispy
    canvas = scene.SceneCanvas(keys='interactive', size=(800, 600), show=False)
    view = canvas.central_widget.add_view()
    view.camera = 'turntable'
    view.camera.fov = 45
    view.camera.distance = 20
    
    # Crear scatter plot
    scatter = scene.visuals.Markers(parent=view.scene)
    
    # Configurar colores basados en densidad
    pos0 = all_data[0]['pos']
    rho0 = all_data[0]['rho']
    
    # Normalizar densidad para colores
    rho_norm = (rho0 - rho0.min()) / (rho0.max() - rho0.min())
    
    # Colormap simple (azul a rojo)
    colors = np.zeros((len(pos0), 4))
    colors[:, 0] = rho_norm  # R
    colors[:, 1] = 0.5 * (1 - rho_norm)  # G
    colors[:, 2] = 1 - rho_norm  # B
    colors[:, 3] = 0.6  # Alpha
    
    scatter.set_data(pos=pos0, face_color=colors, size=PARTICLE_SIZE, edge_width=0)
    
    # Configurar límites de la vista
    max_range = np.max(np.abs(pos0)) * 1.5
    view.camera.set_range((-max_range, max_range), (-max_range, max_range), (-max_range, max_range))
    
    # Capturar frames
    print("Capturando frames...")
    frames = []
    
    for i, data in enumerate(all_data):
        pos = data['pos']
        rho = data['rho']
        
        # Actualizar posiciones y colores
        rho_norm = (rho - rho.min()) / (rho.max() - rho.min())
        colors[:, 0] = rho_norm
        colors[:, 1] = 0.5 * (1 - rho_norm)
        colors[:, 2] = 1 - rho_norm
        
        scatter.set_data(pos=pos, face_color=colors, size=PARTICLE_SIZE, edge_width=0)
        
        # Rotar cámara para efecto 3D
        view.camera.elevation = 30
        view.camera.azimuth = i * 2
        
        # Renderizar y capturar
        canvas.update()
        
        # Capturar frame
        img = canvas.render()
        frames.append(img)
        
        if i % 10 == 0:
            print(f"Frame {i}/{len(all_data)} capturado")
    
    print(f"Capturados {len(frames)} frames")
    
    # Guardar como GIF usando imageio
    try:
        import imageio
        print("Guardando animación...")
        imageio.mimsave(output_file, frames, fps=FPS)
        print(f"Animación guardada: {output_file}")
    except ImportError:
        print("imageio no está instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'imageio'])
        import imageio
        imageio.mimsave(output_file, frames, fps=FPS)
        print(f"Animación guardada: {output_file}")
    
    canvas.close()
    return output_file

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Crear animación GPU de simulación de colisión planetaria')
    parser.add_argument('--output', type=str, default=OUTPUT_FILE, help='Archivo de salida (GIF)')
    parser.add_argument('--fps', type=int, default=FPS, help='Frames por segundo')
    
    args = parser.parse_args()
    
    snapshots = load_snapshots()
    if snapshots:
        create_animation_gpu(snapshots, args.output)
    else:
        print("No se encontraron snapshots. Ejecuta SWIFT primero.")
