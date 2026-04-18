#!/usr/bin/env python3
"""
Generar condiciones iniciales de impacto usando WoMa
Siguiendo el roadmap FASE 2.2
"""

import argparse
from pathlib import Path

import numpy as np
import woma

from planetary_utils import (
    EARTH_MASS_KG,
    body_particle_count,
    build_particle_planet,
    build_differentiated_planet,
    mutual_escape_velocity,
    prepare_output_path,
    recenter_two_body_system,
    require_integer_at_least,
    require_non_negative,
    require_positive,
    save_combined_snapshot,
    save_particle_body,
)

def parse_args():
    parser = argparse.ArgumentParser(description="Generar condiciones iniciales de impacto rocoso")
    parser.add_argument("--target-mass", type=float, default=1.0, help="Masa del target en masas terrestres")
    parser.add_argument("--impactor-mass", type=float, default=None, help="Masa del impactor en masas terrestres")
    parser.add_argument("--impactor-mass-ratio", type=float, default=0.1, help="M_impactor / M_target si no se pasa --impactor-mass")
    parser.add_argument("--target-radius-km", type=float, default=None, help="Radio del target en km")
    parser.add_argument("--impactor-radius-km", type=float, default=None, help="Radio del impactor en km")
    parser.add_argument("--target-particles", type=int, default=40000, help="Número de partículas del target")
    parser.add_argument("--impactor-particles", type=int, default=None, help="Número de partículas del impactor")
    parser.add_argument("--core-mass-fraction", type=float, default=0.325, help="Fracción de masa del núcleo")
    parser.add_argument("--surface-pressure", type=float, default=1e5, help="Presión superficial en Pa")
    parser.add_argument("--surface-temperature", type=float, default=2000.0, help="Temperatura superficial en K")
    parser.add_argument("--impact-angle", type=float, default=45.0, help="Ángulo de impacto en grados")
    parser.add_argument("--velocity-escape", type=float, default=1.1, help="Velocidad de impacto en múltiplos de la velocidad de escape mutua")
    parser.add_argument("--time-before-contact", type=float, default=3600.0, help="Tiempo antes del contacto en segundos")
    parser.add_argument("--seed", type=int, default=12345, help="Semilla base aleatoria")
    parser.add_argument("--boxsize-factor", type=float, default=3.0, help="Factor multiplicativo para el tamaño de caja")
    parser.add_argument("--output", type=Path, default=Path("impact_IC.hdf5"), help="Archivo HDF5 de salida")
    parser.add_argument("--target-output", type=Path, default=None, help="Guardar también el target aislado")
    parser.add_argument("--impactor-output", type=Path, default=None, help="Guardar también el impactor aislado")
    parser.add_argument("--no-entropies", action="store_true", help="No guardar entropías")
    parser.add_argument("--quiet", action="store_true", help="Reducir salida de WoMa")
    return parser.parse_args()

def main():
    args = parse_args()
    verbosity = 0 if args.quiet else 1
    require_positive(args.target_mass, "target_mass")
    if args.impactor_mass is not None:
        require_positive(args.impactor_mass, "impactor_mass")
    else:
        require_positive(args.impactor_mass_ratio, "impactor_mass_ratio")
    require_integer_at_least(args.target_particles, "target_particles")
    if args.impactor_particles is not None:
        require_integer_at_least(args.impactor_particles, "impactor_particles")
    require_positive(args.surface_pressure, "surface_pressure")
    require_positive(args.surface_temperature, "surface_temperature")
    require_positive(args.velocity_escape, "velocity_escape")
    require_non_negative(args.impact_angle, "impact_angle")
    require_positive(args.time_before_contact, "time_before_contact")
    require_positive(args.boxsize_factor, "boxsize_factor")

    target_mass_kg = args.target_mass * EARTH_MASS_KG
    impactor_mass_kg = (
        args.impactor_mass * EARTH_MASS_KG
        if args.impactor_mass is not None
        else args.impactor_mass_ratio * target_mass_kg
    )
    target_radius_m = None if args.target_radius_km is None else args.target_radius_km * 1e3
    impactor_radius_m = None if args.impactor_radius_km is None else args.impactor_radius_km * 1e3

    target_planet = build_differentiated_planet(
        name="target",
        mass_kg=target_mass_kg,
        radius_m=target_radius_m,
        core_mass_fraction=args.core_mass_fraction,
        surface_pressure_pa=args.surface_pressure,
        surface_temperature_k=args.surface_temperature,
        verbosity=verbosity,
    )
    impactor_planet = build_differentiated_planet(
        name="impactor",
        mass_kg=impactor_mass_kg,
        radius_m=impactor_radius_m,
        core_mass_fraction=args.core_mass_fraction,
        surface_pressure_pa=args.surface_pressure,
        surface_temperature_k=args.surface_temperature,
        verbosity=verbosity,
    )

    impactor_particle_count = args.impactor_particles or body_particle_count(
        impactor_planet.M,
        target_planet.M,
        args.target_particles,
    )

    target_particles = build_particle_planet(
        target_planet,
        args.target_particles,
        seed=args.seed,
        verbosity=verbosity,
    )
    impactor_particles = build_particle_planet(
        impactor_planet,
        impactor_particle_count,
        seed=args.seed + 1,
        verbosity=verbosity,
    )

    if args.target_output is not None:
        save_particle_body(
            args.target_output,
            target_particles,
            boxsize_m=10.0 * target_planet.R,
            include_entropies=not args.no_entropies,
            verbosity=verbosity,
        )
    if args.impactor_output is not None:
        save_particle_body(
            args.impactor_output,
            impactor_particles,
            boxsize_m=10.0 * impactor_planet.R,
            include_entropies=not args.no_entropies,
            verbosity=verbosity,
        )

    impact_parameter = np.sin(np.deg2rad(args.impact_angle))
    escape_velocity_m_s = mutual_escape_velocity(
        target_planet.M,
        target_planet.R,
        impactor_planet.M,
        impactor_planet.R,
    )
    impact_velocity_m_s = args.velocity_escape * escape_velocity_m_s

    target_position_m = np.zeros(3)
    target_velocity_m_s = np.zeros(3)
    impactor_position_m, impactor_velocity_m_s = woma.impact_pos_vel_b_v_c_t(
        b=impact_parameter,
        v_c=impact_velocity_m_s,
        t=args.time_before_contact,
        R_t=target_planet.R,
        R_i=impactor_planet.R,
        M_t=target_planet.M,
        M_i=impactor_planet.M,
        units_v_c="m/s",
    )

    (
        target_position_m,
        target_velocity_m_s,
        impactor_position_m,
        impactor_velocity_m_s,
    ) = recenter_two_body_system(
        target_position_m,
        target_velocity_m_s,
        impactor_position_m,
        impactor_velocity_m_s,
        target_planet.M,
        impactor_planet.M,
    )

    initial_separation_m = np.linalg.norm(impactor_position_m - target_position_m)
    boxsize_m = max(
        args.boxsize_factor * initial_separation_m,
        8.0 * (target_planet.R + impactor_planet.R),
    )
    output_path = prepare_output_path(args.output)
    save_combined_snapshot(
        output_path=output_path,
        target_particles=target_particles,
        impactor_particles=impactor_particles,
        target_position_m=target_position_m,
        target_velocity_m_s=target_velocity_m_s,
        impactor_position_m=impactor_position_m,
        impactor_velocity_m_s=impactor_velocity_m_s,
        boxsize_m=boxsize_m,
        include_entropies=not args.no_entropies,
    )

    print(f"Target: M={target_planet.M:.3e} kg, R={target_planet.R / 1e3:.1f} km, N={target_particles.N_particles}")
    print(f"Impactor: M={impactor_planet.M:.3e} kg, R={impactor_planet.R / 1e3:.1f} km, N={impactor_particles.N_particles}")
    print(f"Impact angle: {args.impact_angle:.1f} degrees")
    print(f"Impact parameter b: {impact_parameter:.3f}")
    print(f"Mutual escape velocity: {escape_velocity_m_s / 1e3:.2f} km/s")
    print(f"Impact velocity: {impact_velocity_m_s / 1e3:.2f} km/s")
    print(f"Initial separation: {initial_separation_m / 1e3:.1f} km")
    print(f"Condiciones iniciales guardadas en {output_path}")


if __name__ == "__main__":
    main()
