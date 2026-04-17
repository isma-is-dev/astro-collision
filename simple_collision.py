#!/usr/bin/env python3
"""
Simulación simple de colisión planetaria con N-body puro
Usa numpy para calcular fuerzas gravitacionales y simular la colisión
"""

import numpy as np
import h5py
import time
from datetime import datetime

# Constantes físicas
G = 6.67430e-11  # m^3 kg^-1 s^-2
M_earth = 5.972e24  # kg
R_earth = 6.371e6  # m

class SimpleCollision:
    def __init__(self, n_particles=5000, dt=10.0):
        self.n_particles = n_particles
        self.dt = dt
        self.t = 0.0
        self.snapshot_interval = 100  # guardar cada N pasos
        self.snapshot_count = 0
        
        # Crear dos cuerpos (planetas)
        self.n_target = n_particles // 2
        self.n_impactor = n_particles - self.n_target
        
        # Inicializar partículas
        self.pos = np.zeros((n_particles, 3))
        self.vel = np.zeros((n_particles, 3))
        self.mass = np.ones(n_particles) * (M_earth / n_particles)
        self.material = np.zeros(n_particles, dtype=int)
        
        # Generar planeta target (centro)
        self._generate_sphere(
            np.array([0.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            R_earth,
            self.n_target,
            0
        )
        
        # Generar impactor (colisión diagonal)
        impact_pos = np.array([3.0 * R_earth, 2.0 * R_earth, 0.0])
        impact_vel = np.array([-15000.0, -10000.0, 0.0])  # m/s
        self._generate_sphere(
            impact_pos,
            impact_vel,
            0.5 * R_earth,
            self.n_impactor,
            1
        )
        
        # Aplicar softening para evitar singularidades
        self.softening = 1e5  # m
        
        print(f"Simulación inicializada:")
        print(f"  Partículas: {n_particles}")
        print(f"  Target: {self.n_target} partículas, R={R_earth/1000:.0f} km")
        print(f"  Impactor: {self.n_impactor} partículas, R={0.5*R_earth/1000:.0f} km")
        print(f"  Paso de tiempo: {dt} s")
        
    def _generate_sphere(self, center, velocity, radius, n_particles, material_id):
        """Generar partículas distribuidas uniformemente en una esfera"""
        # Distribución uniforme en esfera
        phi = np.random.uniform(0, 2*np.pi, n_particles)
        costheta = np.random.uniform(-1, 1, n_particles)
        u = np.random.uniform(0, 1, n_particles)
        
        theta = np.arccos(costheta)
        r = radius * np.cbrt(u)
        
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        
        # Asignar rango de partículas
        if material_id == 0:
            idx = slice(0, self.n_target)
        else:
            idx = slice(self.n_target, self.n_particles)
        
        self.pos[idx] = np.column_stack([x, y, z]) + center
        self.vel[idx] = velocity
        self.material[idx] = material_id
        
    def compute_forces(self):
        """Calcular fuerzas gravitacionales N-body"""
        # Usar broadcasting para calcular todas las fuerzas
        # Esto es O(N^2) pero manejable para N ~ 5000
        
        # Diferencias de posición (N, N, 3)
        dx = self.pos[:, np.newaxis, :] - self.pos[np.newaxis, :, :]
        
        # Distancias al cuadrado (N, N)
        r2 = np.sum(dx**2, axis=2) + self.softening**2
        
        # Inversa de la distancia al cubo (N, N)
        inv_r3 = r2**(-1.5)
        
        # Fuerza gravitacional: F = G * m_i * m_j / r^3 * r_vec
        # Aceleración: a_i = sum_j (G * m_j / r^3 * dx)
        
        # Masa * inv_r3 (N, N)
        m_inv_r3 = self.mass[np.newaxis, :] * inv_r3
        
        # Aceleración (N, 3)
        acc = G * np.sum(m_inv_r3[:, :, np.newaxis] * dx, axis=1)
        
        return acc
    
    def step(self):
        """Avanzar un paso de tiempo usando integración leapfrog"""
        # Half-step velocity
        acc = self.compute_forces()
        self.vel += 0.5 * acc * self.dt
        
        # Full-step position
        self.pos += self.vel * self.dt
        
        # Recompute forces
        acc = self.compute_forces()
        
        # Half-step velocity
        self.vel += 0.5 * acc * self.dt
        
        self.t += self.dt
        
        # Guardar snapshot periódicamente
        if self.snapshot_count % self.snapshot_interval == 0:
            self.save_snapshot()
        
        self.snapshot_count += 1
        
    def save_snapshot(self):
        """Guardar snapshot a archivo HDF5"""
        filename = f"simulation_output/snapshot_{self.snapshot_count:06d}.hdf5"
        
        with h5py.File(filename, 'w') as f:
            f.create_dataset('position', data=self.pos)
            f.create_dataset('velocity', data=self.vel)
            f.create_dataset('mass', data=self.mass)
            f.create_dataset('material', data=self.material)
            f.attrs['time'] = self.t
            f.attrs['step'] = self.snapshot_count
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Snapshot {self.snapshot_count}: t={self.t/3600:.2f} h")
        
    def run_indefinitely(self):
        """Correr simulación indefinidamente"""
        print("\nIniciando simulación indefinida...")
        print("Presiona Ctrl+C para detener\n")
        
        try:
            while True:
                self.step()
                
                # Imprimir progreso cada 100 pasos
                if self.snapshot_count % 100 == 0:
                    center_of_mass = np.average(self.pos, axis=0, weights=self.mass)
                    max_distance = np.max(np.linalg.norm(self.pos - center_of_mass, axis=1))
                    print(f"  Paso {self.snapshot_count}: t={self.t/3600:.2f} h, max_r={max_distance/1000:.0f} km")
                    
        except KeyboardInterrupt:
            print("\nSimulación detenida por usuario")
            self.save_snapshot()
            print("Snapshot final guardado")

if __name__ == '__main__':
    # Crear directorio de salida
    import os
    os.makedirs('simulation_output', exist_ok=True)
    
    # Crear y correr simulación
    sim = SimpleCollision(n_particles=5000, dt=50.0)
    sim.run_indefinitely()
