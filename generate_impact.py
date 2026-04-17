#!/usr/bin/env python3
"""
Generar condiciones iniciales de impacto usando WoMa
Siguiendo el roadmap FASE 2.2
"""

import sys
sys.path.insert(0, '/home/ismaelmartin/.codex/astro-emulator/venv/lib/python3.12/site-packages')

import numpy as np
import h5py
import woma

# Constantes
M_earth = 5.972e24
R_earth = 6.371e6

# Cargar el planeta generado (usaremos el mismo archivo para target e impactor)
def load_planet_data(filename):
    with h5py.File(filename, "r") as f:
        # Unidades desde metadatos del archivo
        file_to_SI = woma.Conversions(
            m=float(f["Units"].attrs["Unit mass in cgs (U_M)"][0]) * 1e-3,
            l=float(f["Units"].attrs["Unit length in cgs (U_L)"][0]) * 1e-2,
            t=float(f["Units"].attrs["Unit time in cgs (U_t)"][0]),
        )

        # Datos de partículas (convertidos a SI)
        A2_pos = (
            np.array(f["PartType0/Coordinates"][()])
            - 0.5 * f["Header"].attrs["BoxSize"]
        ) * file_to_SI.l
        A1_m = np.array(f["PartType0/Masses"][()]) * file_to_SI.m
        A1_h = np.array(f["PartType0/SmoothingLengths"][()]) * file_to_SI.l
        A1_rho = np.array(f["PartType0/Densities"][()]) * file_to_SI.rho
        A1_P = np.array(f["PartType0/Pressures"][()]) * file_to_SI.P
        A1_u = np.array(f["PartType0/InternalEnergies"][()]) * file_to_SI.u
        A1_mat_id = np.array(f["PartType0/MaterialIDs"][()])
        A1_s = np.array(f["PartType0/Entropies"][()]) * file_to_SI.s

        return A2_pos, A1_m, A1_h, A1_rho, A1_P, A1_u, A1_mat_id, A1_s, file_to_SI

# Cargar datos del planeta
A2_pos_t, A1_m_t, A1_h_t, A1_rho_t, A1_P_t, A1_u_t, A1_mat_id_t, A1_s_t, file_to_SI = load_planet_data(
    "earth_IC.hdf5"
)

# Para el impactor, usaremos una versión escalada del mismo planeta (más pequeño)
# Escalar posiciones y masas para crear un impactor más pequeño
scale_factor = 0.5  # Impactor 50% del tamaño del target
A2_pos_i = A2_pos_t * scale_factor
A1_m_i = A1_m_t * (scale_factor ** 3)  # Masa escala con volumen
A1_h_i = A1_h_t * scale_factor
A1_rho_i = A1_rho_t  # Densidad se mantiene
A1_P_i = A1_P_t
A1_u_i = A1_u_t
A1_mat_id_i = A1_mat_id_t
A1_s_i = A1_s_t  # Entropía se mantiene

# Calcular masas totales
M_t = np.sum(A1_m_t)
M_i = np.sum(A1_m_i)
R_t = R_earth
R_i = R_earth * scale_factor

print(f"Target: M={M_t:.2e} kg, R={R_t/1000:.2f} km")
print(f"Impactor: M={M_i:.2e} kg, R={R_i/1000:.2f} km")

# Condiciones iniciales de impacto (frame de reposo del target)
# Colisión a 45 grados, velocidad de escape mutua, 1 hora antes del contacto
A1_pos_t, A1_vel_t = np.zeros(3), np.zeros(3)
A1_pos_i, A1_vel_i = woma.impact_pos_vel_b_v_c_t(
    b=np.sin(45 * np.pi / 180),
    v_c=1,
    units_v_c="v_esc",
    t=3600,
    R_t=R_t,
    R_i=R_i,
    M_t=M_t,
    M_i=M_i,
)

print(f"Impact angle: 45 degrees")
print(f"Impact velocity: 1 x escape velocity")
print(f"Time before contact: 1 hour")

# Shift al frame del centro de masa
A1_pos_com = (M_t * A1_pos_t + M_i * A1_pos_i) / (M_t + M_i)
A1_vel_com = (M_t * A1_vel_t + M_i * A1_vel_i) / (M_t + M_i)

A1_pos_t -= A1_pos_com
A1_vel_t -= A1_vel_com
A1_pos_i -= A1_pos_com
A1_vel_i -= A1_vel_com

# Actualizar posiciones de partículas
A2_pos_t[:] += A1_pos_t
A2_vel_t = np.zeros_like(A2_pos_t) + A1_vel_t
A2_pos_i[:] += A1_pos_i
A2_vel_i = np.zeros_like(A2_pos_i) + A1_vel_i

# Combinar y guardar los datos de partículas
output_file = "impact_IC.hdf5"
with h5py.File(output_file, "w") as f:
    woma.save_particle_data(
        f,
        A2_pos=np.append(A2_pos_t, A2_pos_i, axis=0),
        A2_vel=np.append(A2_vel_t, A2_vel_i, axis=0),
        A1_m=np.append(A1_m_t, A1_m_i),
        A1_h=np.append(A1_h_t, A1_h_i),
        A1_rho=np.append(A1_rho_t, A1_rho_i),
        A1_P=np.append(A1_P_t, A1_P_i),
        A1_u=np.append(A1_u_t, A1_u_i),
        A1_mat_id=np.append(A1_mat_id_t, A1_mat_id_i),
        A1_s=np.append(A1_s_t, A1_s_i),
        boxsize=100 * R_earth,
        file_to_SI=woma.Conversions(m=1e24, l=1e6, t=1),
    )

print(f"Condiciones iniciales de impacto guardadas en {output_file}")
print(f"Total partículas: {len(A2_pos_t) + len(A2_pos_i)}")
