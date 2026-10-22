from pathlib import Path
import os
import shlex
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
VENV_PYTHONW = PROJECT_ROOT / "venv" / "Scripts" / "pythonw.exe"
REPO_WSL_SWIFT = PROJECT_ROOT / "swiftsim" / "swift"
NATIVE_SWIFT_CANDIDATES = [
    PROJECT_ROOT / "swiftsim" / "swift.exe",
]
BACKEND_AUTO = "auto"
BACKEND_LOCAL_CPU = "local_cpu"
BACKEND_WSL_CPU = "wsl_cpu"
BACKEND_LABELS = {
    BACKEND_AUTO: "Auto",
    BACKEND_LOCAL_CPU: "CPU local",
    BACKEND_WSL_CPU: "CPU vía WSL",
}
COLOR_CHOICES = ["material", "speed", "mass", "density", "radius"]
PROJECTION_CHOICES = ["xy", "xz", "yz"]
KNOWN_SNAPSHOT_DIRS = [
    "simulation_output",
    "lite_simulation_output",
    "massive_simulation_output",
    "cinematic_output",
    "long_simulation_output",
    "visualization_output",
]


def _unique_strings(values):
    unique = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique



def resolve_project_path(value):
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path



def python_executable(gui=False):
    candidate = VENV_PYTHONW if gui and VENV_PYTHONW.exists() else VENV_PYTHON
    if not candidate.exists():
        raise FileNotFoundError(f"No se encontró el intérprete del entorno virtual: {candidate}")
    return candidate



def find_native_swift():
    for candidate in NATIVE_SWIFT_CANDIDATES:
        if candidate.exists():
            return candidate
    which_swift = shutil.which("swift")
    if which_swift:
        return Path(which_swift)
    return None



def find_wsl_launcher():
    which_wsl = shutil.which("wsl.exe") or shutil.which("wsl")
    if which_wsl:
        return Path(which_wsl)
    return None



def config_files():
    return sorted(path.name for path in PROJECT_ROOT.glob("swift_config*.yml"))



def guess_yaml_value(config_name_or_path, key):
    config_path = resolve_project_path(config_name_or_path)
    if not config_path.exists():
        return ""
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line.startswith(f"{key}:"):
            continue
        return line.split(":", 1)[1].strip()
    return ""



def guess_yaml_float_value(config_name_or_path, key, default=None):
    value = guess_yaml_value(config_name_or_path, key)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default



def guess_snapshot_subdir_from_config(config_name_or_path):
    return guess_yaml_value(config_name_or_path, "subdir")



def estimate_snapshot_count(config_name_or_path):
    time_end = guess_yaml_float_value(config_name_or_path, "time_end")
    time_first = guess_yaml_float_value(config_name_or_path, "time_first", default=0.0)
    delta_time = guess_yaml_float_value(config_name_or_path, "delta_time")
    if time_end is None or delta_time is None or delta_time <= 0.0:
        return None
    if time_end < time_first:
        return 0
    return int((time_end - time_first) // delta_time) + 1



def snapshot_dirs():
    ordered = []
    ordered.extend(KNOWN_SNAPSHOT_DIRS)
    for config_name in config_files():
        subdir = guess_snapshot_subdir_from_config(config_name)
        if subdir:
            ordered.append(subdir)
    for path in PROJECT_ROOT.iterdir():
        if not path.is_dir():
            continue
        if path.name.endswith("_output") or path.name in {"simulation_output", "visualization_output"}:
            ordered.append(path.name)
    return _unique_strings(ordered)



def preferred_snapshot_dir():
    dirs = snapshot_dirs()
    return dirs[0] if dirs else "simulation_output"



def to_wsl_path(value):
    path = Path(value).resolve()
    if path.drive:
        drive = path.drive.rstrip(":").lower()
        tail = path.as_posix()[2:]
        return f"/mnt/{drive}{tail}"
    return path.as_posix()



def default_thread_count():
    cpu_count = os.cpu_count() or 2
    return max(1, min(2, cpu_count))



def detect_environment():
    native_swift = find_native_swift()
    wsl_launcher = find_wsl_launcher()
    repo_wsl_swift = REPO_WSL_SWIFT.exists() and REPO_WSL_SWIFT.is_file()

    if native_swift is not None:
        recommended_backend = BACKEND_LOCAL_CPU
        recommendation = "SWIFT nativo detectado en Windows."
    elif wsl_launcher is not None and repo_wsl_swift:
        recommended_backend = BACKEND_WSL_CPU
        recommendation = "Binario Linux de SWIFT detectado en el repositorio; WSL es la mejor opción."
    elif wsl_launcher is not None:
        recommended_backend = BACKEND_AUTO
        recommendation = "WSL está disponible, pero no hay un binario SWIFT verificado. Puedes usar CPU vía WSL si tienes SWIFT en PATH o indicas un override."
    else:
        recommended_backend = BACKEND_AUTO
        recommendation = "No se detectó un backend ejecutable de SWIFT en este momento."

    return {
        "project_root": str(PROJECT_ROOT),
        "venv_python": str(VENV_PYTHON),
        "venv_python_exists": VENV_PYTHON.exists(),
        "venv_pythonw_exists": VENV_PYTHONW.exists(),
        "native_swift": str(native_swift) if native_swift is not None else "",
        "native_swift_exists": native_swift is not None,
        "wsl_launcher": str(wsl_launcher) if wsl_launcher is not None else "",
        "wsl_exists": wsl_launcher is not None,
        "repo_wsl_swift": str(REPO_WSL_SWIFT) if repo_wsl_swift else "",
        "repo_wsl_swift_exists": repo_wsl_swift,
        "recommended_backend": recommended_backend,
        "recommended_backend_label": BACKEND_LABELS.get(recommended_backend, BACKEND_LABELS[BACKEND_AUTO]),
        "recommendation": recommendation,
        "gpu_status": "No soportada por el solver actual de este proyecto.",
        "configs": config_files(),
        "snapshot_dirs": snapshot_dirs(),
    }



def environment_status_text(environment):
    parts = [
        f"venv: {'OK' if environment['venv_python_exists'] else 'NO'}",
        f"SWIFT local: {'OK' if environment['native_swift_exists'] else 'NO'}",
        f"WSL: {'OK' if environment['wsl_exists'] else 'NO'}",
        f"SWIFT Linux repo: {'OK' if environment['repo_wsl_swift_exists'] else 'NO'}",
        f"Backend recomendado: {environment['recommended_backend_label']}",
    ]
    return " | ".join(parts)



def format_command(command):
    return " ".join(f'"{item}"' if " " in item else item for item in command)



def _append_option(command, flag, value):
    if isinstance(value, bool):
        if value:
            command.append(flag)
        return
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    command.extend([flag, text])



def build_python_script_command(script_name, options):
    script_path = PROJECT_ROOT / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"No se encontró el script: {script_path}")
    command = [str(python_executable()), str(script_path)]
    for flag, value in options.items():
        _append_option(command, flag, value)
    return command



def build_generate_earth_command(options):
    ordered_options = {
        "--mass": options.get("mass"),
        "--radius-km": options.get("radius_km"),
        "--particles": options.get("particles"),
        "--core-mass-fraction": options.get("core_mass_fraction"),
        "--surface-pressure": options.get("surface_pressure"),
        "--surface-temperature": options.get("surface_temperature"),
        "--seed": options.get("seed"),
        "--boxsize-factor": options.get("boxsize_factor"),
        "--output": options.get("output"),
        "--no-entropies": options.get("no_entropies"),
        "--quiet": options.get("quiet"),
    }
    return build_python_script_command("generate_earth.py", ordered_options)



def build_generate_impact_command(options):
    ordered_options = {
        "--target-mass": options.get("target_mass"),
        "--impactor-mass": options.get("impactor_mass"),
        "--impactor-mass-ratio": options.get("impactor_mass_ratio"),
        "--target-radius-km": options.get("target_radius_km"),
        "--impactor-radius-km": options.get("impactor_radius_km"),
        "--target-particles": options.get("target_particles"),
        "--impactor-particles": options.get("impactor_particles"),
        "--core-mass-fraction": options.get("core_mass_fraction"),
        "--surface-pressure": options.get("surface_pressure"),
        "--surface-temperature": options.get("surface_temperature"),
        "--impact-angle": options.get("impact_angle"),
        "--velocity-escape": options.get("velocity_escape"),
        "--time-before-contact": options.get("time_before_contact"),
        "--seed": options.get("seed"),
        "--boxsize-factor": options.get("boxsize_factor"),
        "--output": options.get("output"),
        "--target-output": options.get("target_output"),
        "--impactor-output": options.get("impactor_output"),
        "--no-entropies": options.get("no_entropies"),
        "--quiet": options.get("quiet"),
    }
    return build_python_script_command("generate_impact.py", ordered_options)



def build_visualize_command(options):
    ordered_options = {
        "--all": options.get("all_snapshots"),
        "--snapshot": options.get("snapshot"),
        "--snapshot-dir": options.get("snapshot_dir"),
        "--output": options.get("output"),
        "--output-dir": options.get("output_dir"),
        "--projection": options.get("projection"),
        "--color-by": options.get("color_by"),
        "--max-particles": options.get("max_particles"),
        "--dpi": options.get("dpi"),
    }
    return build_python_script_command("visualize.py", ordered_options)



def build_animate_command(options):
    ordered_options = {
        "--output": options.get("output"),
        "--fps": options.get("fps"),
        "--skip": options.get("skip"),
        "--snapshot-dir": options.get("snapshot_dir"),
        "--projection": options.get("projection"),
        "--color-by": options.get("color_by"),
        "--max-particles": options.get("max_particles"),
        "--dpi": options.get("dpi"),
    }
    return build_python_script_command("animate.py", ordered_options)



def _native_swift_command(swift_executable):
    override = str(swift_executable or "").strip()
    if override:
        candidate = resolve_project_path(override)
        if candidate.exists():
            return str(candidate)
        return override
    detected = find_native_swift()
    if detected is None:
        raise FileNotFoundError("No se encontró un binario SWIFT nativo para Windows.")
    return str(detected)



def _wsl_swift_command(swift_executable):
    override = str(swift_executable or "").strip()
    if override:
        if len(override) > 1 and override[1] == ":":
            return shlex.quote(to_wsl_path(override))
        return override
    if REPO_WSL_SWIFT.exists():
        return "./swiftsim/swift"
    return "swift"



def build_swift_command(config_name_or_path, threads, backend=BACKEND_AUTO, swift_executable=""):
    environment = detect_environment()
    config_path = resolve_project_path(config_name_or_path)
    if not config_path.exists():
        raise FileNotFoundError(f"No se encontró la configuración SWIFT: {config_path}")

    selected_backend = backend if backend and backend != BACKEND_AUTO else environment["recommended_backend"]
    thread_count = max(1, int(threads))

    if selected_backend == BACKEND_LOCAL_CPU:
        swift_command = _native_swift_command(swift_executable)
        return [swift_command, "--hydro", "--self-gravity", "-t", str(thread_count), "-s", str(config_path)], selected_backend

    if selected_backend == BACKEND_WSL_CPU:
        wsl_launcher = find_wsl_launcher()
        if wsl_launcher is None:
            raise FileNotFoundError("WSL no está disponible en este sistema.")
        swift_command = _wsl_swift_command(swift_executable)
        bash_command = " && ".join(
            [
                f"cd {shlex.quote(to_wsl_path(PROJECT_ROOT))}",
                f"{swift_command} --hydro --self-gravity -t {thread_count} -s {shlex.quote(to_wsl_path(config_path))}",
            ]
        )
        return [str(wsl_launcher), "bash", "-lc", bash_command], selected_backend

    raise FileNotFoundError(
        "No hay un backend de SWIFT utilizable. Instala SWIFT nativo para Windows o usa WSL con el binario Linux."
    )
