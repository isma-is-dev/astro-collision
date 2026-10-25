#!/usr/bin/env python3
"""
Simulación de colisión planetaria con PySPH usando GPU
"""

import sys
sys.path.insert(0, '/home/ismaelmartin/.codex/astro-emulator/venv/lib/python3.12/site-packages')

import numpy as np
import h5py
from pysph.base.utils import get_particle_array_wcsph
from pysph.solver.application import Application
from pysph.sph.scheme import WCSPHScheme
from pysph.base.kernels import CubicSpline

# Constantes
M_earth = 5.972e24  # kg
R_earth = 6.371e6   # m
G = 6.67430e-11     # m^3 kg^-1 s^-2

def load_woma_data(filename):
    """Cargar datos de WoMa desde archivo HDF5"""
    with h5py.File(filename, 'r') as f:
        # Unidades
        m_unit = float(f["Units"].attrs["Unit mass in cgs (U_M)"][0]) * 1e-3  # kg
        l_unit = float(f["Units"].attrs["Unit length in cgs (U_L)"][0]) * 1e-2  # m
        t_unit = float(f["Units"].attrs["Unit time in cgs (U_t)"][0])  # s
        
        # Partículas
        pos = np.array(f["PartType0/Coordinates"][()])
        vel = np.array(f["PartType0/Velocities"][()])
        m = np.array(f["PartType0/Masses"][()])
        h = np.array(f["PartType0/SmoothingLengths"][()])
        rho = np.array(f["PartType0/Densities"][()])
        u = np.array(f["PartType0/InternalEnergies"][()])
        mat_id = np.array(f["PartType0/MaterialIDs"][()])
        
        # Convertir a unidades SI
        pos = pos * l_unit
        vel = vel * (l_unit / t_unit)
        m = m * m_unit
        h = h * l_unit
        rho = rho * (m_unit / l_unit**3)
        u = u * (l_unit**2 / t_unit**2)
        
        return pos, vel, m, h, rho, u, mat_id

class PlanetaryCollision(Application):
    def initialize(self):
        # Parámetros de la simulación
        self.rho0 = 4000.0  # kg/m^3 (densidad típica de roca)
        self.c0 = 10000.0   # m/s (velocidad del sonido en roca - más alta para estabilidad)
        self.hdx = 1.5
        self.dx = R_earth / 15.0  # Espaciado de partículas
        self.gamma = 5.0/3.0
        self.alpha = 0.5
        self.beta = 1.0
        
        # Tiempo de simulación
        self.dt = 0.1  # segundos (más pequeño para estabilidad)
        self.tf = 10.0  # segundos (simulación más corta)
        
        print(f"Parámetros: rho0={self.rho0}, c0={self.c0}, dx={self.dx/R_earth} R_earth")

    def create_scheme(self):
        s = WCSPHScheme(
            ['fluid'], [], dim=3, 
            rho0=self.rho0, c0=self.c0,
            h0=self.dx*self.hdx, hdx=self.hdx, 
            gamma=self.gamma, 
            alpha=self.alpha, beta=self.beta,
            gz=-9.81  # Gravedad (opcional)
        )
        s.configure_solver(dt=self.dt, tf=self.tf)
        return s

    def create_particles(self):
        """Cargar partículas desde WoMa"""
        print("Cargando datos de WoMa...")
        
        # Cargar datos del impactor
        pos, vel, m, h, rho, u, mat_id = load_woma_data("impact_IC.hdf5")
        
        print(f"Partículas cargadas: {len(pos)}")
        print(f"Posiciones: min={np.min(pos/R_earth):.2f}, max={np.max(pos/R_earth):.2f} R_earth")
        print(f"Velocidades: min={np.min(vel):.2f}, max={np.max(vel):.2f} m/s")
        print(f"Densidades: min={np.min(rho):.2f}, max={np.max(rho):.2f} kg/m^3")
        
        # Crear ParticleArray de PySPH con todas las propiedades necesarias
        fluid = get_particle_array_wcsph(
            name='fluid',
            x=pos[:, 0],
            y=pos[:, 1], 
            z=pos[:, 2],
            m=m,
            h=h,
            rho=rho,
            u=u
        )
        
        # Configurar propiedades del esquema primero
        self.scheme.setup_properties([fluid])
        
        # Asignar velocidades después de configurar propiedades
        # Verificar estructura de la propiedad de velocidad
        if 'v' in fluid.properties:
            v_prop = fluid.v
            print(f"Shape de propiedad v: {v_prop.shape}")
            if v_prop.shape == (len(pos), 3):
                fluid.v[:] = vel
            elif v_prop.shape == (len(pos),):
                # Si es 1D, probablemente no es la propiedad correcta para 3D
                print("Advertencia: propiedad 'v' es 1D, buscando vx, vy, vz")
                if 'vx' in fluid.properties:
                    fluid.vx[:] = vel[:, 0]
                    fluid.vy[:] = vel[:, 1]
                    fluid.vz[:] = vel[:, 2]
                else:
                    print("No se encontraron propiedades de velocidad 3D")
        elif 'vx' in fluid.properties:
            fluid.vx[:] = vel[:, 0]
            fluid.vy[:] = vel[:, 1]
            fluid.vz[:] = vel[:, 2]
        else:
            print("Advertencia: v/vx no disponible en properties")
            print("Propiedades disponibles:", list(fluid.properties.keys()))
        
        # Configurar propiedades límite
        fluid.set_lb_props(list(fluid.properties.keys()))
        
        # Habilitar GPU si está disponible
        if fluid.gpu:
            print("GPU disponible, habilitando aceleración...")
            fluid.gpu.push()
        else:
            print("GPU no disponible, usando CPU")
        
        return [fluid]

if __name__ == '__main__':
    app = PlanetaryCollision()
    app.run()
