from pathlib import Path
import inspect
import math

import h5py
import numpy as np
import woma

EARTH_MASS_KG = 5.972e24
EARTH_RADIUS_M = 6.371e6
G_SI = 6.67430e-11
DEFAULT_FILE_TO_SI = woma.Conversions(m=1e24, l=1e6, t=1.0)
_SEAGEN_COMPAT_PATCHED = False


def prepare_output_path(output_path):
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def require_positive(value, name):
    numeric_value = float(value)
    if numeric_value <= 0.0:
        raise ValueError(f"{name} must be positive")
    return value


def require_non_negative(value, name):
    numeric_value = float(value)
    if numeric_value < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return value


def require_integer_at_least(value, name, minimum=1):
    integer_value = int(value)
    if integer_value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return integer_value


def ensure_seagen_compatibility():
    global _SEAGEN_COMPAT_PATCHED
    if _SEAGEN_COMPAT_PATCHED:
        return

    import seagen

    original_init = seagen.GenSphere.__init__
    if "Di_param_A1_misc_prof" in inspect.signature(original_init).parameters:
        _SEAGEN_COMPAT_PATCHED = True
        return

    def patched_gen_sphere(self, *args, **kwargs):
        kwargs.pop("Di_param_A1_misc_prof", None)
        return original_init(self, *args, **kwargs)

    seagen.GenSphere.__init__ = patched_gen_sphere
    _SEAGEN_COMPAT_PATCHED = True


def earth_like_radius_from_mass(mass_kg):
    require_positive(mass_kg, "mass_kg")
    return EARTH_RADIUS_M * (mass_kg / EARTH_MASS_KG) ** 0.27


def mutual_escape_velocity(target_mass_kg, target_radius_m, impactor_mass_kg, impactor_radius_m):
    return math.sqrt(
        2.0 * G_SI * (target_mass_kg + impactor_mass_kg) / (target_radius_m + impactor_radius_m)
    )


def body_particle_count(body_mass_kg, reference_mass_kg, reference_particles, minimum_particles=1000):
    require_positive(body_mass_kg, "body_mass_kg")
    require_positive(reference_mass_kg, "reference_mass_kg")
    reference_particles = require_integer_at_least(reference_particles, "reference_particles")
    minimum_particles = require_integer_at_least(minimum_particles, "minimum_particles")
    scaled_particles = int(round(reference_particles * body_mass_kg / reference_mass_kg))
    return max(minimum_particles, scaled_particles)


def build_differentiated_planet(
    name,
    mass_kg,
    radius_m=None,
    core_mass_fraction=0.325,
    surface_pressure_pa=1e5,
    surface_temperature_k=2000.0,
    core_material="Til_iron",
    mantle_material="Til_granite",
    verbosity=1,
):
    require_positive(mass_kg, "mass_kg")
    if not 0.0 < core_mass_fraction < 1.0:
        raise ValueError("core_mass_fraction must be between 0 and 1")
    if radius_m is not None:
        require_positive(radius_m, "radius_m")
    require_positive(surface_pressure_pa, "surface_pressure_pa")
    require_positive(surface_temperature_k, "surface_temperature_k")

    radius_guess_m = radius_m or earth_like_radius_from_mass(mass_kg)
    planet = woma.Planet(
        name=name,
        A1_mat_layer=[core_material, mantle_material],
        A1_T_rho_type=["power=0", "power=0"],
        P_s=surface_pressure_pa,
        T_s=surface_temperature_k,
        M=mass_kg,
        R=radius_guess_m,
        A1_M_layer=[core_mass_fraction * mass_kg, (1.0 - core_mass_fraction) * mass_kg],
        verbosity=verbosity,
    )

    planet.gen_prof_L2_find_R1_given_M_R(verbosity=verbosity)

    return planet


def build_particle_planet(planet, particle_count, seed=12345, verbosity=1):
    particle_count = require_integer_at_least(particle_count, "particle_count")
    ensure_seagen_compatibility()
    return woma.ParticlePlanet(planet, particle_count, seed=seed, verbosity=verbosity)


def recenter_two_body_system(
    target_position_m,
    target_velocity_m_s,
    impactor_position_m,
    impactor_velocity_m_s,
    target_mass_kg,
    impactor_mass_kg,
):
    require_positive(target_mass_kg, "target_mass_kg")
    require_positive(impactor_mass_kg, "impactor_mass_kg")
    total_mass_kg = target_mass_kg + impactor_mass_kg
    center_of_mass_position = (
        target_mass_kg * target_position_m + impactor_mass_kg * impactor_position_m
    ) / total_mass_kg
    center_of_mass_velocity = (
        target_mass_kg * target_velocity_m_s + impactor_mass_kg * impactor_velocity_m_s
    ) / total_mass_kg

    return (
        target_position_m - center_of_mass_position,
        target_velocity_m_s - center_of_mass_velocity,
        impactor_position_m - center_of_mass_position,
        impactor_velocity_m_s - center_of_mass_velocity,
    )


def ensure_entropies(particles):
    if not hasattr(particles, "A1_s"):
        try:
            particles.calculate_entropies()
        except ValueError:
            return None
    return particles.A1_s


def save_particle_body(output_path, particles, boxsize_m, include_entropies=False, verbosity=1):
    output_path = prepare_output_path(output_path)
    save_entropies = include_entropies and ensure_entropies(particles) is not None
    particles.save(
        str(output_path),
        boxsize=boxsize_m,
        file_to_SI=DEFAULT_FILE_TO_SI,
        do_entropies=save_entropies,
        verbosity=verbosity,
    )
    return output_path


def save_combined_snapshot(
    output_path,
    target_particles,
    impactor_particles,
    target_position_m,
    target_velocity_m_s,
    impactor_position_m,
    impactor_velocity_m_s,
    boxsize_m,
    include_entropies=False,
):
    output_path = prepare_output_path(output_path)
    target_positions = target_particles.A2_pos + target_position_m
    impactor_positions = impactor_particles.A2_pos + impactor_position_m
    target_velocities = target_particles.A2_vel + target_velocity_m_s
    impactor_velocities = impactor_particles.A2_vel + impactor_velocity_m_s

    entropies = None
    if include_entropies:
        target_entropies = ensure_entropies(target_particles)
        impactor_entropies = ensure_entropies(impactor_particles)
        if target_entropies is not None and impactor_entropies is not None:
            entropies = np.concatenate([target_entropies, impactor_entropies])

    with h5py.File(output_path, "w") as handle:
        woma.save_particle_data(
            handle,
            A2_pos=np.concatenate([target_positions, impactor_positions], axis=0),
            A2_vel=np.concatenate([target_velocities, impactor_velocities], axis=0),
            A1_m=np.concatenate([target_particles.A1_m, impactor_particles.A1_m]),
            A1_h=np.concatenate([target_particles.A1_h, impactor_particles.A1_h]),
            A1_rho=np.concatenate([target_particles.A1_rho, impactor_particles.A1_rho]),
            A1_P=np.concatenate([target_particles.A1_P, impactor_particles.A1_P]),
            A1_u=np.concatenate([target_particles.A1_u, impactor_particles.A1_u]),
            A1_mat_id=np.concatenate([target_particles.A1_mat_id, impactor_particles.A1_mat_id]),
            A1_s=entropies,
            boxsize=boxsize_m,
            file_to_SI=DEFAULT_FILE_TO_SI,
        )


def discover_snapshots(snapshot_dir):
    snapshot_dir = Path(snapshot_dir)
    if not snapshot_dir.exists():
        return []

    snapshots = []
    for pattern in ("snapshot_*.hdf5", "impact_*.hdf5", "*.hdf5"):
        snapshots.extend(snapshot_dir.glob(pattern))

    unique_snapshots = sorted({path.resolve() for path in snapshots})
    return [Path(path) for path in unique_snapshots]


def snapshot_time_hours(snapshot):
    return float(snapshot.get("time_s", 0.0)) / 3600.0


def sample_indices(num_particles, max_particles, seed=12345):
    if max_particles is None or num_particles <= max_particles:
        return np.arange(num_particles)
    rng = np.random.default_rng(seed + num_particles)
    return np.sort(rng.choice(num_particles, size=max_particles, replace=False))


def subset_snapshot(snapshot, indices):
    subset = {}
    particle_count = len(snapshot["position_m"])

    for key, value in snapshot.items():
        if isinstance(value, np.ndarray) and len(value) == particle_count:
            subset[key] = value[indices]
        else:
            subset[key] = value

    return subset


def color_values(snapshot, color_by):
    if color_by == "material":
        return snapshot["material"].astype(float), "Material ID"
    if color_by == "speed":
        return np.linalg.norm(snapshot["velocity_m_s"], axis=1), "Speed (m/s)"
    if color_by == "mass":
        return snapshot["mass_kg"], "Mass (kg)"
    if color_by == "density":
        density = snapshot.get("density_kg_m3")
        if density is None:
            return snapshot["mass_kg"], "Mass (kg)"
        return density, "Density (kg/m^3)"
    if color_by == "radius":
        return np.linalg.norm(snapshot["position_m"], axis=1), "Radius (m)"
    raise ValueError(f"Unsupported color_by value: {color_by}")


def project_positions(position_m, projection):
    if projection == "xy":
        return position_m[:, 0], position_m[:, 1], "X (R_earth)", "Y (R_earth)"
    if projection == "xz":
        return position_m[:, 0], position_m[:, 2], "X (R_earth)", "Z (R_earth)"
    if projection == "yz":
        return position_m[:, 1], position_m[:, 2], "Y (R_earth)", "Z (R_earth)"
    raise ValueError(f"Unsupported projection: {projection}")


def _as_float(value, default=0.0):
    if value is None:
        return float(default)
    array_value = np.asarray(value)
    return float(array_value.reshape(-1)[0])


def _swift_unit_scales(handle):
    if "Units" not in handle:
        return {
            "mass_kg": 1.0,
            "length_m": 1.0,
            "time_s": 1.0,
            "velocity_m_s": 1.0,
            "density_kg_m3": 1.0,
        }

    units = handle["Units"].attrs
    mass_kg = _as_float(units.get("Unit mass in cgs (U_M)")) * 1e-3
    length_m = _as_float(units.get("Unit length in cgs (U_L)")) * 1e-2
    time_s = _as_float(units.get("Unit time in cgs (U_t)"), default=1.0)

    return {
        "mass_kg": mass_kg,
        "length_m": length_m,
        "time_s": time_s,
        "velocity_m_s": length_m / time_s,
        "density_kg_m3": mass_kg / (length_m ** 3),
    }


def load_snapshot(snapshot_path):
    snapshot_path = Path(snapshot_path)
    with h5py.File(snapshot_path, "r") as handle:
        if "PartType0" in handle:
            units = _swift_unit_scales(handle)
            particles = handle["PartType0"]
            header = handle["Header"].attrs
            boxsize = np.asarray(header.get("BoxSize", [0.0, 0.0, 0.0]), dtype=np.float64)
            boxsize_m = boxsize * units["length_m"]
            position_m = np.asarray(particles["Coordinates"], dtype=np.float64)
            if np.any(boxsize_m > 0.0):
                position_m = position_m - 0.5 * boxsize
            position_m = position_m * units["length_m"]
            velocity_m_s = np.asarray(particles["Velocities"], dtype=np.float64) * units["velocity_m_s"]
            mass_kg = np.asarray(particles["Masses"], dtype=np.float64) * units["mass_kg"]
            material = np.asarray(particles["MaterialIDs"], dtype=np.int64)
            density_kg_m3 = None
            if "Densities" in particles:
                density_kg_m3 = (
                    np.asarray(particles["Densities"], dtype=np.float64) * units["density_kg_m3"]
                )
            time_s = _as_float(header.get("Time", [0.0])) * units["time_s"]
            return {
                "path": snapshot_path,
                "format": "swift",
                "position_m": position_m,
                "velocity_m_s": velocity_m_s,
                "mass_kg": mass_kg,
                "material": material,
                "density_kg_m3": density_kg_m3,
                "time_s": time_s,
            }

        position_m = np.asarray(handle["position"], dtype=np.float64)
        velocity_m_s = np.asarray(handle["velocity"], dtype=np.float64)
        mass_kg = np.asarray(handle["mass"], dtype=np.float64)
        material = np.asarray(handle["material"], dtype=np.int64)
        time_s = _as_float(handle.attrs.get("time", 0.0))
        return {
            "path": snapshot_path,
            "format": "simple",
            "position_m": position_m,
            "velocity_m_s": velocity_m_s,
            "mass_kg": mass_kg,
            "material": material,
            "density_kg_m3": None,
            "time_s": time_s,
        }
