#!/usr/bin/env python3
"""
Generar un planeta tipo Tierra usando WoMa
Siguiendo el roadmap FASE 2.1 y ejemplo de SWIFT
"""

import sys
sys.path.insert(0, '/home/ismaelmartin/.codex/astro-emulator/venv/lib/python3.12/site-packages')

import woma
import numpy as np

# Constantes
M_earth = 5.972e24
R_earth = 6.371e6

# Definir planeta simple de 1 capa (basalto) para empezar
planet = woma.Planet(
    name="earth_like",
    A1_mat_layer=["Til_basalt"],  # material: basalto Tillotson
    A1_T_rho_type=["power=0"],    # temperatura constante
    P_s=1e5,                      # presión superficial en Pa
    T_s=500,                      # temperatura superficial en K
    M=M_earth,                    # masa en kg
)

# Cargar tablas de EoS
woma.load_eos_tables(planet.A1_mat_layer)

# Generar perfil de equilibrio hidrostático
planet.gen_prof_L1_find_R_given_M(R_max=2 * R_earth)

print(f"Planeta generado: {planet.name}")
print(f"Radio total: {planet.R/1000:.2f} km")
print(f"Masa total: {planet.M:.2e} kg")

# Generar partículas (usando menos partículas para prueba rápida)
N_particles = 10000  # 10k partículas para test rápido
particles = woma.ParticlePlanet(planet, N_particles, seed=12345)

print(f"Número de partículas: {particles.N_particles}")

# Guardar en archivo HDF5 con conversiones de unidades
file_to_SI = woma.Conversions(m=1e24, l=1e6, t=1)
output_file = "/home/ismaelmartin/.codex/astro-emulator/earth_IC.hdf5"
particles.save(
    output_file,
    boxsize=10 * R_earth,
    file_to_SI=file_to_SI,
    do_entropies=True,
)

print(f"Partículas guardadas en {output_file}")
