#!/usr/bin/env python3
"""
Generar un planeta tipo Tierra usando WoMa
Siguiendo el roadmap FASE 2.1 y ejemplo de SWIFT
"""

import argparse
from pathlib import Path

import numpy as np

from planetary_utils import (
    EARTH_MASS_KG,
    build_differentiated_planet,
    build_particle_planet,
    require_integer_at_least,
    require_positive,
    save_particle_body,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Generar un planeta rocoso diferenciado tipo Tierra")
    parser.add_argument("--mass", type=float, default=1.0, help="Masa total en masas terrestres")
    parser.add_argument("--radius-km", type=float, default=None, help="Radio total en km")
    parser.add_argument("--particles", type=int, default=20000, help="Número de partículas SPH")
    parser.add_argument("--core-mass-fraction", type=float, default=0.325, help="Fracción de masa del núcleo")
    parser.add_argument("--surface-pressure", type=float, default=1e5, help="Presión superficial en Pa")
    parser.add_argument("--surface-temperature", type=float, default=2000.0, help="Temperatura superficial en K")
    parser.add_argument("--seed", type=int, default=12345, help="Semilla aleatoria")
    parser.add_argument("--boxsize-factor", type=float, default=10.0, help="Tamaño de caja en radios planetarios")
    parser.add_argument("--output", type=Path, default=Path("earth_IC.hdf5"), help="Archivo HDF5 de salida")
    parser.add_argument("--no-entropies", action="store_true", help="No guardar entropías")
    parser.add_argument("--quiet", action="store_true", help="Reducir salida de WoMa")
    return parser.parse_args()


def main():
    args = parse_args()
    verbosity = 0 if args.quiet else 1
    require_positive(args.mass, "mass")
    require_integer_at_least(args.particles, "particles")
    require_positive(args.boxsize_factor, "boxsize_factor")
    mass_kg = args.mass * EARTH_MASS_KG
    radius_m = None if args.radius_km is None else args.radius_km * 1e3

    planet = build_differentiated_planet(
        name="earth_like",
        mass_kg=mass_kg,
        radius_m=radius_m,
        core_mass_fraction=args.core_mass_fraction,
        surface_pressure_pa=args.surface_pressure,
        surface_temperature_k=args.surface_temperature,
        verbosity=verbosity,
    )

    particles = build_particle_planet(planet, args.particles, seed=args.seed, verbosity=verbosity)
    output_path = save_particle_body(
        args.output,
        particles,
        boxsize_m=args.boxsize_factor * planet.R,
        include_entropies=not args.no_entropies,
        verbosity=verbosity,
    )

    mean_density = planet.M / ((4.0 / 3.0) * np.pi * planet.R ** 3)
    print(f"Planeta generado: {planet.name}")
    print(f"Radio total: {planet.R / 1e3:.1f} km")
    print(f"Masa total: {planet.M:.3e} kg")
    print(f"Densidad media: {mean_density:.1f} kg/m^3")
    print(f"Número de partículas: {particles.N_particles}")
    print(f"Partículas guardadas en {output_path}")


if __name__ == "__main__":
    main()
