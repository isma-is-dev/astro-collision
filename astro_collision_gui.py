from pathlib import Path
import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app_controller import (
    BACKEND_AUTO,
    BACKEND_LABELS,
    BACKEND_LOCAL_CPU,
    BACKEND_WSL_CPU,
    COLOR_CHOICES,
    PROJECT_ROOT,
    PROJECTION_CHOICES,
    build_animate_command,
    build_generate_earth_command,
    build_generate_impact_command,
    build_swift_command,
    build_visualize_command,
    default_thread_count,
    detect_environment,
    estimate_snapshot_count,
    environment_status_text,
    format_command,
    guess_snapshot_subdir_from_config,
    preferred_snapshot_dir,
)


class AstroCollisionGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Astro Collision Control Panel")
        self.geometry("1260x900")
        self.minsize(1100, 760)
        self.environment = detect_environment()
        self.log_queue = queue.Queue()
        self.current_process = None
        self.current_title = ""
        self.status_var = tk.StringVar()
        self.recommendation_var = tk.StringVar()
        self.config_summary_var = tk.StringVar()
        self.gpu_var = tk.StringVar()
        self.process_var = tk.StringVar(value="Sin proceso en ejecución")
        self._create_variables()
        self._build_ui()
        self.refresh_environment()
        self.after(120, self._poll_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_variables(self):
        default_snapshot_dir = preferred_snapshot_dir()
        default_config = "swift_config.yml" if "swift_config.yml" in self.environment["configs"] else (self.environment["configs"][0] if self.environment["configs"] else "swift_config.yml")

        self.earth_mass_var = tk.StringVar(value="1.0")
        self.earth_radius_var = tk.StringVar(value="")
        self.earth_particles_var = tk.StringVar(value="20000")
        self.earth_core_fraction_var = tk.StringVar(value="0.325")
        self.earth_pressure_var = tk.StringVar(value="1e5")
        self.earth_temperature_var = tk.StringVar(value="2000")
        self.earth_seed_var = tk.StringVar(value="12345")
        self.earth_boxsize_var = tk.StringVar(value="10.0")
        self.earth_output_var = tk.StringVar(value="earth_IC.hdf5")
        self.earth_no_entropies_var = tk.BooleanVar(value=False)
        self.earth_quiet_var = tk.BooleanVar(value=False)

        self.impact_target_mass_var = tk.StringVar(value="1.0")
        self.impact_impactor_mass_var = tk.StringVar(value="")
        self.impact_impactor_ratio_var = tk.StringVar(value="0.1")
        self.impact_target_radius_var = tk.StringVar(value="")
        self.impact_impactor_radius_var = tk.StringVar(value="")
        self.impact_target_particles_var = tk.StringVar(value="40000")
        self.impact_impactor_particles_var = tk.StringVar(value="")
        self.impact_core_fraction_var = tk.StringVar(value="0.325")
        self.impact_pressure_var = tk.StringVar(value="1e5")
        self.impact_temperature_var = tk.StringVar(value="2000")
        self.impact_angle_var = tk.StringVar(value="45")
        self.impact_velocity_escape_var = tk.StringVar(value="1.1")
        self.impact_time_before_contact_var = tk.StringVar(value="3600")
        self.impact_seed_var = tk.StringVar(value="12345")
        self.impact_boxsize_var = tk.StringVar(value="3.0")
        self.impact_output_var = tk.StringVar(value="impact_IC.hdf5")
        self.impact_no_entropies_var = tk.BooleanVar(value=False)
        self.impact_quiet_var = tk.BooleanVar(value=False)

        self.simulation_config_var = tk.StringVar(value=default_config)
        self.simulation_backend_var = tk.StringVar(value=self.environment["recommended_backend"])
        self.simulation_threads_var = tk.StringVar(value=str(default_thread_count()))
        self.simulation_swift_var = tk.StringVar(value="")
        self.simulation_output_dir_var = tk.StringVar(value=guess_snapshot_subdir_from_config(default_config) or default_snapshot_dir)

        self.visualize_snapshot_var = tk.StringVar(value="")
        self.visualize_snapshot_dir_var = tk.StringVar(value=default_snapshot_dir)
        self.visualize_projection_var = tk.StringVar(value="xy")
        self.visualize_color_var = tk.StringVar(value="material")
        self.visualize_particles_var = tk.StringVar(value="25000")
        self.visualize_dpi_var = tk.StringVar(value="140")
        self.visualize_output_var = tk.StringVar(value="")
        self.visualize_output_dir_var = tk.StringVar(value="visualization_output")

        self.animate_snapshot_dir_var = tk.StringVar(value=default_snapshot_dir)
        self.animate_projection_var = tk.StringVar(value="xy")
        self.animate_color_var = tk.StringVar(value="material")
        self.animate_particles_var = tk.StringVar(value="15000")
        self.animate_dpi_var = tk.StringVar(value="120")
        self.animate_output_var = tk.StringVar(value="collision_animation.gif")
        self.animate_fps_var = tk.StringVar(value="10")
        self.animate_skip_var = tk.StringVar(value="1")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=12)
        header.grid(row=0, column=0, sticky="nsew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.recommendation_var).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(header, textvariable=self.config_summary_var).grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(header, textvariable=self.gpu_var).grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Label(header, textvariable=self.process_var).grid(row=4, column=0, sticky="w", pady=(4, 0))

        header_actions = ttk.Frame(header)
        header_actions.grid(row=0, column=1, rowspan=5, sticky="ne")
        ttk.Button(header_actions, text="Refrescar entorno", command=self.refresh_environment).grid(row=0, column=0, padx=(0, 6), pady=2)
        ttk.Button(header_actions, text="Abrir proyecto", command=lambda: self._open_path(PROJECT_ROOT)).grid(row=0, column=1, padx=(0, 6), pady=2)
        ttk.Button(header_actions, text="Detener proceso", command=self.stop_process).grid(row=0, column=2, pady=2)

        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=12)

        generation_tab = ttk.Frame(notebook, padding=12)
        simulation_tab = ttk.Frame(notebook, padding=12)
        visualization_tab = ttk.Frame(notebook, padding=12)
        animation_tab = ttk.Frame(notebook, padding=12)

        notebook.add(generation_tab, text="Generación")
        notebook.add(simulation_tab, text="Simulación")
        notebook.add(visualization_tab, text="Visualización")
        notebook.add(animation_tab, text="Animación")

        self._build_generation_tab(generation_tab)
        self._build_simulation_tab(simulation_tab)
        self._build_visualization_tab(visualization_tab)
        self._build_animation_tab(animation_tab)

        log_frame = ttk.Labelframe(self, text="Salida y logs", padding=12)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(8, 12))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, wrap="word", height=16)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        log_actions = ttk.Frame(log_frame)
        log_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(log_actions, text="Limpiar log", command=self._clear_log).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(log_actions, text="Abrir carpeta de snapshots", command=self.open_selected_snapshot_dir).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(log_actions, text="Abrir salida de simulación", command=self.open_selected_output_dir).grid(row=0, column=2)

    def _build_generation_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        earth_frame = ttk.Labelframe(parent, text="Planeta aislado", padding=12)
        earth_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        impact_frame = ttk.Labelframe(parent, text="Impacto target-impactor", padding=12)
        impact_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._entry_row(earth_frame, 0, "Masa (M⊕)", self.earth_mass_var)
        self._entry_row(earth_frame, 1, "Radio (km, opcional)", self.earth_radius_var)
        self._entry_row(earth_frame, 2, "Partículas", self.earth_particles_var)
        self._entry_row(earth_frame, 3, "Fracción núcleo", self.earth_core_fraction_var)
        self._entry_row(earth_frame, 4, "Presión superficial", self.earth_pressure_var)
        self._entry_row(earth_frame, 5, "Temperatura superficial", self.earth_temperature_var)
        self._entry_row(earth_frame, 6, "Seed", self.earth_seed_var)
        self._entry_row(earth_frame, 7, "Factor boxsize", self.earth_boxsize_var)
        self._entry_row(earth_frame, 8, "Salida HDF5", self.earth_output_var, width=28)
        ttk.Checkbutton(earth_frame, text="Sin entropías", variable=self.earth_no_entropies_var).grid(row=9, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(earth_frame, text="Modo silencioso", variable=self.earth_quiet_var).grid(row=9, column=1, sticky="w", pady=(8, 0))
        ttk.Button(earth_frame, text="Generar planeta", command=self.run_generate_earth).grid(row=10, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        self._entry_row(impact_frame, 0, "Target masa (M⊕)", self.impact_target_mass_var)
        self._entry_row(impact_frame, 1, "Impactor masa (M⊕, opcional)", self.impact_impactor_mass_var)
        self._entry_row(impact_frame, 2, "Impactor ratio", self.impact_impactor_ratio_var)
        self._entry_row(impact_frame, 3, "Target radio (km, opcional)", self.impact_target_radius_var)
        self._entry_row(impact_frame, 4, "Impactor radio (km, opcional)", self.impact_impactor_radius_var)
        self._entry_row(impact_frame, 5, "Target partículas", self.impact_target_particles_var)
        self._entry_row(impact_frame, 6, "Impactor partículas", self.impact_impactor_particles_var)
        self._entry_row(impact_frame, 7, "Ángulo impacto", self.impact_angle_var)
        self._entry_row(impact_frame, 8, "Velocidad / v_escape", self.impact_velocity_escape_var)
        self._entry_row(impact_frame, 9, "Tiempo antes contacto", self.impact_time_before_contact_var)
        self._entry_row(impact_frame, 10, "Fracción núcleo", self.impact_core_fraction_var)
        self._entry_row(impact_frame, 11, "Presión superficial", self.impact_pressure_var)
        self._entry_row(impact_frame, 12, "Temperatura superficial", self.impact_temperature_var)
        self._entry_row(impact_frame, 13, "Seed", self.impact_seed_var)
        self._entry_row(impact_frame, 14, "Factor boxsize", self.impact_boxsize_var)
        self._entry_row(impact_frame, 15, "Salida HDF5", self.impact_output_var, width=28)
        ttk.Checkbutton(impact_frame, text="Sin entropías", variable=self.impact_no_entropies_var).grid(row=16, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(impact_frame, text="Modo silencioso", variable=self.impact_quiet_var).grid(row=16, column=1, sticky="w", pady=(8, 0))
        ttk.Button(impact_frame, text="Generar impacto", command=self.run_generate_impact).grid(row=17, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_simulation_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        self.config_combo = self._combo_row(parent, 0, "Config SWIFT", self.simulation_config_var, self.environment["configs"], width=36)
        self.config_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_output_dir_from_config())
        self._combo_row(parent, 1, "Backend", self.simulation_backend_var, [BACKEND_AUTO, BACKEND_LOCAL_CPU, BACKEND_WSL_CPU], width=24)
        self._entry_row(parent, 2, "Threads", self.simulation_threads_var)
        self._entry_row(parent, 3, "SWIFT override", self.simulation_swift_var, width=42)
        self._entry_row(parent, 4, "Directorio de salida", self.simulation_output_dir_var, width=36)
        ttk.Button(parent, text="Lanzar SWIFT", command=self.run_swift).grid(row=5, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(parent, text="Abrir config seleccionada", command=self.open_selected_config).grid(row=6, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(parent, text="Abrir carpeta de salida", command=self.open_selected_output_dir).grid(row=7, column=0, sticky="ew", pady=(6, 0))
        backend_info = ttk.Labelframe(parent, text="Estrategia CPU / GPU", padding=12)
        backend_info.grid(row=0, column=1, rowspan=8, sticky="nsew", padx=(18, 0))
        backend_info.columnconfigure(0, weight=1)
        ttk.Label(backend_info, text="CPU local:").grid(row=0, column=0, sticky="w")
        self.native_swift_label = ttk.Label(backend_info, text="")
        self.native_swift_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Label(backend_info, text="CPU vía WSL:").grid(row=2, column=0, sticky="w")
        self.wsl_swift_label = ttk.Label(backend_info, text="")
        self.wsl_swift_label.grid(row=3, column=0, sticky="w", pady=(0, 8))
        ttk.Label(backend_info, text="GPU:").grid(row=4, column=0, sticky="w")
        self.gpu_status_label = ttk.Label(backend_info, text="")
        self.gpu_status_label.grid(row=5, column=0, sticky="w", pady=(0, 8))
        ttk.Label(backend_info, text="Recomendación:").grid(row=6, column=0, sticky="w")
        self.recommendation_label = ttk.Label(backend_info, text="", wraplength=360)
        self.recommendation_label.grid(row=7, column=0, sticky="w")

    def _build_visualization_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        self.visualize_snapshot_dir_combo = self._combo_row(parent, 0, "Directorio snapshots", self.visualize_snapshot_dir_var, self.environment["snapshot_dirs"], width=36)
        self._entry_row(parent, 1, "Snapshot específico", self.visualize_snapshot_var, width=42)
        self._combo_row(parent, 2, "Proyección", self.visualize_projection_var, PROJECTION_CHOICES)
        self._combo_row(parent, 3, "Color por", self.visualize_color_var, COLOR_CHOICES)
        self._entry_row(parent, 4, "Máx. partículas", self.visualize_particles_var)
        self._entry_row(parent, 5, "DPI", self.visualize_dpi_var)
        self._entry_row(parent, 6, "Salida PNG", self.visualize_output_var, width=42)
        self._entry_row(parent, 7, "Directorio para todos", self.visualize_output_dir_var, width=42)
        ttk.Button(parent, text="Render último snapshot", command=self.run_visualize_latest).grid(row=8, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(parent, text="Render snapshot específico", command=self.run_visualize_specific).grid(row=9, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(parent, text="Render todos", command=self.run_visualize_all).grid(row=10, column=0, sticky="ew", pady=(6, 0))

    def _build_animation_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        self.animate_snapshot_dir_combo = self._combo_row(parent, 0, "Directorio snapshots", self.animate_snapshot_dir_var, self.environment["snapshot_dirs"], width=36)
        self._combo_row(parent, 1, "Proyección", self.animate_projection_var, PROJECTION_CHOICES)
        self._combo_row(parent, 2, "Color por", self.animate_color_var, COLOR_CHOICES)
        self._entry_row(parent, 3, "Máx. partículas", self.animate_particles_var)
        self._entry_row(parent, 4, "DPI", self.animate_dpi_var)
        self._entry_row(parent, 5, "FPS", self.animate_fps_var)
        self._entry_row(parent, 6, "Skip", self.animate_skip_var)
        self._entry_row(parent, 7, "Salida GIF/MP4", self.animate_output_var, width=42)
        ttk.Button(parent, text="Crear animación", command=self.run_animation).grid(row=8, column=0, sticky="ew", pady=(12, 0))

    def _entry_row(self, parent, row, label, variable, width=18):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=variable, width=width)
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(12, 0))
        return entry

    def _combo_row(self, parent, row, label, variable, values, width=18):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        combo = ttk.Combobox(parent, textvariable=variable, values=list(values), width=width, state="normal")
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=(12, 0))
        return combo

    def refresh_environment(self):
        self.environment = detect_environment()
        self.status_var.set(environment_status_text(self.environment))
        self.recommendation_var.set(self.environment["recommendation"])
        self.gpu_var.set(f"GPU: {self.environment['gpu_status']}")
        self.native_swift_label.configure(text=self.environment["native_swift"] or "No detectado")
        wsl_text = self.environment["repo_wsl_swift"] or self.environment["wsl_launcher"] or "No detectado"
        self.wsl_swift_label.configure(text=wsl_text)
        self.gpu_status_label.configure(text=self.environment["gpu_status"])
        self.recommendation_label.configure(text=self.environment["recommendation"])
        if not self.simulation_backend_var.get() or self.simulation_backend_var.get() == BACKEND_AUTO:
            self.simulation_backend_var.set(self.environment["recommended_backend"])
        config_values = self.environment["configs"] or ["swift_config.yml"]
        snapshot_values = self.environment["snapshot_dirs"] or [preferred_snapshot_dir()]
        self.config_combo.configure(values=config_values)
        self.visualize_snapshot_dir_combo.configure(values=snapshot_values)
        self.animate_snapshot_dir_combo.configure(values=snapshot_values)
        if self.simulation_config_var.get() not in config_values:
            self.simulation_config_var.set(config_values[0])
        if self.visualize_snapshot_dir_var.get() not in snapshot_values:
            self.visualize_snapshot_dir_var.set(snapshot_values[0])
        if self.animate_snapshot_dir_var.get() not in snapshot_values:
            self.animate_snapshot_dir_var.set(snapshot_values[0])
        self._sync_output_dir_from_config()

    def _sync_output_dir_from_config(self):
        subdir = guess_snapshot_subdir_from_config(self.simulation_config_var.get())
        expected_snapshots = estimate_snapshot_count(self.simulation_config_var.get())
        if subdir:
            self.simulation_output_dir_var.set(subdir)
            if not self.visualize_snapshot_dir_var.get():
                self.visualize_snapshot_dir_var.set(subdir)
            if not self.animate_snapshot_dir_var.get():
                self.animate_snapshot_dir_var.set(subdir)
        if self.simulation_backend_var.get() == BACKEND_WSL_CPU:
            try:
                current_threads = int(self.simulation_threads_var.get())
            except ValueError:
                current_threads = 0
            if current_threads <= 0 or current_threads > 2:
                self.simulation_threads_var.set("2")
        if expected_snapshots is None:
            self.config_summary_var.set(f"Config activa: {self.simulation_config_var.get()} | Snapshots esperados: desconocido")
        else:
            self.config_summary_var.set(f"Config activa: {self.simulation_config_var.get()} | Snapshots esperados: ~{expected_snapshots}")

    def _append_log(self, text):
        self.log_text.insert("end", text)
        self.log_text.see("end")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")

    def _poll_log_queue(self):
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            kind = item[0]
            if kind == "line":
                self._append_log(item[1])
            elif kind == "done":
                _, title, return_code = item
                if return_code == 0:
                    self.process_var.set(f"Proceso finalizado: {title} (código {return_code})")
                    self._append_log(f"\n[FIN] {title} -> código {return_code}\n")
                else:
                    self.process_var.set(f"Proceso fallido: {title} (código {return_code})")
                    self._append_log(f"\n[ERROR] {title} -> código {return_code}\n")
                    if return_code == 139 and "SWIFT" in title:
                        self._append_log("[DIAGNÓSTICO] SWIFT se ha caído antes de completar la integración. Si la config guarda snapshots cada mucho tiempo, solo verás snapshot_0000.hdf5. En este proyecto, usa 2 hilos como punto de partida para WSL.\n")
                self.refresh_environment()
            elif kind == "error":
                self.process_var.set("Proceso fallido")
                self._append_log(f"\n[ERROR] {item[1]}\n")
            elif kind == "status":
                self.process_var.set(item[1])
        self.after(120, self._poll_log_queue)

    def _start_process(self, title, command):
        if self.current_process is not None and self.current_process.poll() is None:
            messagebox.showwarning("Proceso en ejecución", "Ya hay un proceso en ejecución. Deténlo antes de lanzar otro.")
            return

        self.current_title = title
        self._append_log(f"\n=== {title} ===\n{format_command(command)}\n\n")

        def worker():
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.current_process = process
                self.log_queue.put(("status", f"Ejecutando: {title}"))
                if process.stdout is not None:
                    for line in process.stdout:
                        self.log_queue.put(("line", line))
                return_code = process.wait()
                self.log_queue.put(("done", title, return_code))
            except Exception as exc:
                self.log_queue.put(("error", f"{title}: {exc}"))
            finally:
                self.current_process = None
                self.current_title = ""

        threading.Thread(target=worker, daemon=True).start()

    def stop_process(self):
        if self.current_process is None or self.current_process.poll() is not None:
            messagebox.showinfo("Sin proceso", "No hay ningún proceso activo.")
            return
        try:
            self.current_process.terminate()
            self._append_log("\n[INFO] Señal de parada enviada al proceso activo.\n")
        except Exception as exc:
            messagebox.showerror("No se pudo detener", str(exc))

    def run_generate_earth(self):
        command = build_generate_earth_command(
            {
                "mass": self.earth_mass_var.get(),
                "radius_km": self.earth_radius_var.get(),
                "particles": self.earth_particles_var.get(),
                "core_mass_fraction": self.earth_core_fraction_var.get(),
                "surface_pressure": self.earth_pressure_var.get(),
                "surface_temperature": self.earth_temperature_var.get(),
                "seed": self.earth_seed_var.get(),
                "boxsize_factor": self.earth_boxsize_var.get(),
                "output": self.earth_output_var.get(),
                "no_entropies": self.earth_no_entropies_var.get(),
                "quiet": self.earth_quiet_var.get(),
            }
        )
        self._start_process("Generar planeta aislado", command)

    def run_generate_impact(self):
        command = build_generate_impact_command(
            {
                "target_mass": self.impact_target_mass_var.get(),
                "impactor_mass": self.impact_impactor_mass_var.get(),
                "impactor_mass_ratio": self.impact_impactor_ratio_var.get(),
                "target_radius_km": self.impact_target_radius_var.get(),
                "impactor_radius_km": self.impact_impactor_radius_var.get(),
                "target_particles": self.impact_target_particles_var.get(),
                "impactor_particles": self.impact_impactor_particles_var.get(),
                "core_mass_fraction": self.impact_core_fraction_var.get(),
                "surface_pressure": self.impact_pressure_var.get(),
                "surface_temperature": self.impact_temperature_var.get(),
                "impact_angle": self.impact_angle_var.get(),
                "velocity_escape": self.impact_velocity_escape_var.get(),
                "time_before_contact": self.impact_time_before_contact_var.get(),
                "seed": self.impact_seed_var.get(),
                "boxsize_factor": self.impact_boxsize_var.get(),
                "output": self.impact_output_var.get(),
                "no_entropies": self.impact_no_entropies_var.get(),
                "quiet": self.impact_quiet_var.get(),
            }
        )
        self._start_process("Generar impacto", command)

    def run_swift(self):
        if self.simulation_backend_var.get() == BACKEND_WSL_CPU:
            try:
                requested_threads = int(self.simulation_threads_var.get())
            except ValueError:
                requested_threads = 0
            if requested_threads > 2:
                proceed = messagebox.askyesno(
                    "Hilos altos en WSL",
                    "Has pedido más de 2 hilos para SWIFT vía WSL. En este proyecto ya se ha visto un crash temprano con código 139 usando 6 hilos. ¿Quieres continuar igualmente?",
                )
                if not proceed:
                    return
        try:
            command, selected_backend = build_swift_command(
                self.simulation_config_var.get(),
                self.simulation_threads_var.get(),
                backend=self.simulation_backend_var.get(),
                swift_executable=self.simulation_swift_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("No se pudo lanzar SWIFT", str(exc))
            return
        backend_label = BACKEND_LABELS.get(selected_backend, selected_backend)
        self._start_process(f"SWIFT ({backend_label})", command)

    def run_visualize_latest(self):
        command = build_visualize_command(
            {
                "snapshot_dir": self.visualize_snapshot_dir_var.get(),
                "output": self.visualize_output_var.get(),
                "projection": self.visualize_projection_var.get(),
                "color_by": self.visualize_color_var.get(),
                "max_particles": self.visualize_particles_var.get(),
                "dpi": self.visualize_dpi_var.get(),
            }
        )
        self._start_process("Render último snapshot", command)

    def run_visualize_specific(self):
        if not self.visualize_snapshot_var.get().strip():
            messagebox.showwarning("Falta snapshot", "Indica un snapshot específico para esta acción.")
            return
        command = build_visualize_command(
            {
                "snapshot": self.visualize_snapshot_var.get(),
                "output": self.visualize_output_var.get(),
                "projection": self.visualize_projection_var.get(),
                "color_by": self.visualize_color_var.get(),
                "max_particles": self.visualize_particles_var.get(),
                "dpi": self.visualize_dpi_var.get(),
            }
        )
        self._start_process("Render snapshot específico", command)

    def run_visualize_all(self):
        command = build_visualize_command(
            {
                "all_snapshots": True,
                "snapshot_dir": self.visualize_snapshot_dir_var.get(),
                "output_dir": self.visualize_output_dir_var.get(),
                "projection": self.visualize_projection_var.get(),
                "color_by": self.visualize_color_var.get(),
                "max_particles": self.visualize_particles_var.get(),
                "dpi": self.visualize_dpi_var.get(),
            }
        )
        self._start_process("Render todos los snapshots", command)

    def run_animation(self):
        command = build_animate_command(
            {
                "output": self.animate_output_var.get(),
                "fps": self.animate_fps_var.get(),
                "skip": self.animate_skip_var.get(),
                "snapshot_dir": self.animate_snapshot_dir_var.get(),
                "projection": self.animate_projection_var.get(),
                "color_by": self.animate_color_var.get(),
                "max_particles": self.animate_particles_var.get(),
                "dpi": self.animate_dpi_var.get(),
            }
        )
        self._start_process("Crear animación", command)

    def open_selected_config(self):
        self._open_path(PROJECT_ROOT / self.simulation_config_var.get())

    def open_selected_output_dir(self):
        self._open_path(PROJECT_ROOT / self.simulation_output_dir_var.get())

    def open_selected_snapshot_dir(self):
        self._open_path(PROJECT_ROOT / self.visualize_snapshot_dir_var.get())

    def _open_path(self, path):
        target = Path(path)
        if not target.exists():
            messagebox.showwarning("Ruta no encontrada", str(target))
            return
        try:
            os.startfile(str(target))
        except AttributeError:
            subprocess.Popen(["explorer", str(target)])
        except Exception as exc:
            messagebox.showerror("No se pudo abrir la ruta", str(exc))

    def _on_close(self):
        if self.current_process is not None and self.current_process.poll() is None:
            if not messagebox.askyesno("Proceso activo", "Hay un proceso en ejecución. ¿Quieres cerrar igualmente?"):
                return
        self.destroy()


if __name__ == "__main__":
    AstroCollisionGUI().mainloop()
