# Roadmap Técnico: Simulador de Colisiones Planetarias Realista en Hardware Común

> **Objetivo:** Construir un simulador capaz de reproducir colisiones tipo Tierra-Theia, Júpiter-Júpiter, o cuerpo supramasivo → estrella → agujero negro, con física real (SPH + N-body + EoS multi-material), ejecutable en un PC moderno de consumo (8–16 cores, 16–64 GB RAM, GPU opcional).

---

## Visión general del stack

```
[WoMa]  →  condiciones iniciales (planetas en equilibrio hidrostático)
   ↓
[SWIFT] →  simulación SPH + gravedad (N-body + Fast Multipole Method)
   ↓
[swiftsimio + matplotlib / yt / ParaView]  →  análisis y visualización
```

Todo open-source. Todo en C/Python. Todo corre en un portátil potente o un desktop.

---

## FASE 0 — Fundamentos teóricos mínimos (1–2 semanas)

Antes de tocar código, hay que entender los tres pilares. No hace falta dominarlos matemáticamente, pero sí saber qué hace cada uno y por qué falla si se configura mal.

### 0.1 SPH (Smoothed Particle Hydrodynamics)

SPH es un método **lagrangiano sin malla**: el fluido se discretiza en partículas que se mueven con el flujo. Cada partícula lleva masa, posición, velocidad, energía interna y material. Las propiedades en cualquier punto se estiman como un promedio ponderado de las partículas vecinas usando un **kernel** de suavizado.

Las ecuaciones fundamentales que SWIFT resuelve son conservación de masa, momento y energía:

```
Dρ/Dt = -ρ ∇·v
Dv/Dt = -∇P/ρ + g
Du/Dt = -P/ρ ∇·v + Γ_visc
```

Donde g viene del solver gravitatorio y Γ_visc es la viscosidad artificial (necesaria para capturar ondas de choque sin inestabilidades).

**Por qué SPH para colisiones planetarias:**
- No hay malla → el vacío interplanetario no cuesta nada
- Lagrangiano → puedes rastrear de dónde vino cada fragmento
- Maneja automáticamente geometrías complejas (planetas fragmentándose, chorros de material)

**Problema clásico de SPH y cómo se resuelve en SWIFT:**
- El SPH estándar tiene errores en las discontinuidades de densidad entre capas (manto-núcleo). SWIFT implementa **REMIX SPH** y el esquema **Density-Energy multi-material** para mitigarlo.

### 0.2 Gravedad N-body con Fast Multipole Method (FMM)

Para N partículas, la fuerza gravitatoria exacta es O(N²). SWIFT usa un **FMM** con expansiones multipolares: agrupa partículas lejanas y aproxima su atracción con un multipolo de orden configurable. Coste: O(N log N) o incluso O(N) con FMM completo.

Para 10⁴–10⁶ partículas en 2 cuerpos esto es trivial para un PC moderno.

### 0.3 Ecuación de Estado (EoS)

La EoS relaciona densidad y energía interna con presión: P = P(ρ, u). Es lo que diferencia hierro de granito de hidrógeno gaseoso. Sin una EoS realista, todos los planetas se comportan igual.

**EoS usadas en SWIFT para colisiones planetarias:**
- **Tillotson**: la más usada, semi-analítica, barata, válida para materiales rocosos/metálicos. Implementada para hierro, granito, basalto, agua.
- **ANEOS**: tabular, más precisa, válida en condiciones extremas (fundido, vapor). Disponible para forsterita, hierro, agua.
- **SESAME**: tabular de laboratorio nacional (Los Alamos). Cubre rangos extremos.
- **Hubbard & MacFarlane (1980)**: específica para gas/hielo de planetas gigantes (Urano, Neptuno).
- **CMS19 / CD21**: hidrógeno y helio de Júpiter (tabla de Chabrier). Fundamental para gigantes gaseosos.

**Decisión de diseño clave:** para rocosos usa Tillotson (barato, bueno). Para Júpiter/gigantes gaseosos usa CMS19_H + CMS19_He (tabular). Para el escenario "se volvió estrella / agujero negro" necesitarás una EoS de gas ideal o radiativa + umbrales de estado físico (ver Fase 4).

---

## FASE 1 — Instalación del entorno (1–3 días)

### 1.1 Dependencias del sistema

```bash
# Ubuntu/Debian
sudo apt install build-essential cmake git python3-pip python3-dev
sudo apt install libhdf5-dev libfftw3-dev libgsl-dev libopenmpi-dev
sudo apt install libtbb-dev  # para paralelismo por tareas en SWIFT

# macOS (con Homebrew)
brew install cmake hdf5 fftw gsl open-mpi tbb
```

### 1.2 Compilar SWIFT

```bash
git clone https://github.com/SWIFTSIM/SWIFT.git
cd SWIFT
./autogen.sh

./configure \
  --with-hydro=planetary \          # activa el esquema SPH multi-material
  --with-equation-of-state=planetary \  # activa EoS Tillotson/ANEOS/SESAME
  --with-gravity=fmm \              # Fast Multipole Method para gravedad
  --enable-planetary-fixed-entropy \  # fija entropía en CI si se desea
  --with-tbb \                       # paralelismo por tareas (para CPU multi-core)
  --disable-mpi                      # sin MPI para uso local simple

make -j$(nproc)
```

**¿Cuántos cores usa SWIFT en tu PC?** Con --with-tbb, SWIFT usa todos los cores disponibles automáticamente mediante su sistema de task-based parallelism. En un i7/Ryzen de 8 cores verás ~6–7x speedup sobre 1 core.

### 1.3 Descargar tablas EoS

```bash
cd examples/Planetary/EoSTables
bash get_eos_tables.sh  # descarga tablas ANEOS, SESAME, etc. (~200 MB)
```

### 1.4 Instalar WoMa y herramientas Python

```bash
pip install woma seagen swiftsimio h5py numpy scipy matplotlib
```

---

## FASE 2 — Generar condiciones iniciales con WoMa (3–5 días)

WoMa resuelve las **ecuaciones de equilibrio hidrostático** para construir un planeta en capas con perfil de densidad/temperatura/presión consistente, y luego coloca partículas SPH que replican ese perfil con densidades SPH correctas (usando SEAGen).

### 2.1 Crear un planeta rocoso tipo Tierra

```python
import woma

# Definir planeta: núcleo de hierro + manto de granito
planet = woma.Planet(
    name="earth_like",
    A1_mat_layer=["Til_iron", "Til_granite"],  # materiales por capa
    A1_T_rho_type=["adiabatic", "adiabatic"],  # perfil de temperatura
    A1_R_layer=[0.55, 1.0],                    # radios (fracciones del total)
    M=5.972e24,                                # masa en kg
)
planet.gen_prof_L2_find_R_R1_given_M_M1(
    M=5.972e24,
    M_frac_1=0.325,   # fracción de masa del núcleo (32.5% para la Tierra)
)

# Generar partículas
particles = woma.ParticleSet(planet, N_particles=1e5)  # 100k partículas para test
particles.save("earth_IC.hdf5")
```

### 2.2 Crear Júpiter (gas gigante diferenciado)

```python
# Júpiter: núcleo rocoso + capa de hielo + envuelta H/He
planet_jupiter = woma.Planet(
    name="jupiter_like",
    A1_mat_layer=["ANEOS_iron", "AQUA", "CD21_HHe"],
    A1_T_rho_type=["adiabatic", "adiabatic", "adiabatic"],
    A1_R_layer=[0.12, 0.25, 1.0],
    M=1.898e27,
)
planet_jupiter.gen_prof_L3_find_R_R1_R2_given_M_M1_M2(
    M=1.898e27,
    M_frac_1=0.03,   # ~3% núcleo rocoso
    M_frac_2=0.07,   # ~7% capa hielo/agua
)
particles_jupiter = woma.ParticleSet(planet_jupiter, N_particles=5e4)
particles_jupiter.save("jupiter_IC.hdf5")
```

### 2.3 Configurar geometría de impacto

WoMa incluye funciones para calcular posiciones y velocidades iniciales dado un ángulo de impacto y velocidad:

```python
R_target = planet.R        # radio del objetivo
R_impactor = planet2.R     # radio del impactor
M_target = planet.M
M_impactor = planet2.M

# b = parámetro de impacto (0=frontal, 1=tangencial)
# v_c = velocidad de impacto en m/s (típicamente 1–2× v_escape)
pos_i, vel_i = woma.impact_pos_vel_b_v_c_r(
    b=0.7,
    v_c=1.5 * woma.v_escape(M_target, R_target),
    r=4 * R_target,       # distancia inicial (4 radios del objetivo)
    R_t=R_target,
    R_i=R_impactor,
    M_t=M_target,
    M_i=M_impactor,
)

# Combinar los dos HDF5 en un archivo de condiciones iniciales
woma.combine_planet_snapshots(
    "earth_IC.hdf5", "impactor_IC.hdf5",
    pos_2=pos_i, vel_2=vel_i,
    output="impact_IC.hdf5"
)
```

### 2.4 Relajación previa (opcional pero recomendada)

Antes de la colisión, conviene dejar que cada planeta se "relaje" individualmente durante un tiempo corto (~un periodo de sonido) para eliminar ruido numérico de la generación de partículas. Esto es una simulación corta de SWIFT con solo un planeta.

---

## FASE 3 — Ejecutar la simulación con SWIFT (1–3 días de configuración + horas/días de cómputo)

### 3.1 Archivo de parámetros YAML

```yaml
# impact_params.yml

MetaData:
  run_name: jupiter_earth_collision

InternalUnitSystem:
  UnitMass_in_cgs:     1.98848e33    # masa solar en g
  UnitLength_in_cgs:   6.957e10      # radio solar en cm
  UnitVelocity_in_cgs: 1e5           # 1 km/s

Cosmology:
  Omega_m: 0.
  Omega_lambda: 0.

TimeIntegration:
  time_begin: 0.0
  time_end: 5e4          # en segundos (escalado según unidades)
  dt_min: 1e-6
  dt_max: 10.0

Gravity:
  eta:          0.025    # softening gravitacional relativo
  theta_cr:     0.7      # criterio de apertura del árbol FMM
  comoving_DM_softening: 0.

SPH:
  resolution_eta: 1.2348   # radio kernel / separación partículas (48 vecinos)
  CFL_condition:  0.6       # número de Courant
  h_min_ratio:    0.01
  h_max_ratio:    10.

PlanetaryHydro:
  viscosity_alpha: 1.5
  viscosity_beta:  3.0

Snapshots:
  basename:     output/snapshot
  time_first:   0.
  delta_time:   500.0    # guardar cada ~500 s simulados

Scheduler:
  max_top_level_cells: 64
  cell_split_size:     200

Restarts:
  enable:      1
  delta_hours: 1.0       # checkpoint cada hora de CPU
```

### 3.2 Lanzar la simulación

```bash
mkdir output
./swift --hydro --self-gravity \
        --threads=$(nproc) \
        impact_params.yml 2>&1 | tee simulation.log
```

**Tiempos orientativos en hardware común (AMD Ryzen 9 / Intel i9, 16 cores):**

| N partículas | Tiempo simulado | Tiempo CPU |
|---|---|---|
| 10⁴ | impacto completo | ~5 min |
| 10⁵ | impacto completo | ~1–2 h |
| 10⁶ | impacto completo | ~12–24 h |
| 10⁷ | impacto completo | ~1–2 semanas (necesita cluster) |

Para exploración interactiva usa 10⁴–10⁵. Para publicación/referencia usa 10⁶+.

### 3.3 Acelerar con GPU (opcional)

SWIFT tiene soporte experimental GPU vía CUDA para el cálculo de fuerzas SPH. Alternativamente, usa **pkdgrav3** que tiene soporte GPU maduro:

```bash
# pkdgrav3: alternativa a SWIFT con soporte GPU híbrido CPU/GPU
git clone https://bitbucket.org/dpotter/pkdgrav3
# Compilar con -DUSE_CUDA=ON si tienes NVIDIA
```

En una RTX 3080/4070 puedes esperar 10–20x speedup sobre CPU para el cálculo SPH.

---

## FASE 4 — Física avanzada: estrella, agujero negro, regímenes extremos

Esta fase es donde entra la lógica de "creé un Júpiter demasiado masivo".

### 4.1 Transición planeta → estrella (fusión nuclear simplificada)

No necesitas relatividad general ni MHD completa. Un modelo simplificado pero físicamente motivado:

```python
# Threshold de ignición de hidrógeno: ~0.08 M_solar = 1.6e29 kg
M_stellar_threshold = 0.08 * 1.989e30

def classify_object(mass, central_density, central_temp):
    if mass < 1e27:          return "rocky_planet"
    elif mass < 1.3e28:      return "gas_giant"
    elif mass < 0.08 * 1.989e30:  return "brown_dwarf"    # no fusión
    elif mass < 1.4 * 1.989e30:   return "main_sequence_star"  # fusión H
    elif mass < 3.0 * 1.989e30:   return "neutron_star_progenitor"
    else:                    return "black_hole_progenitor"
```

En SWIFT puedes implementar esto como un **sub-grid model**: cuando la densidad central supera un umbral, cambiar la EoS a gas ideal con presión de radiación incluida, y añadir una fuente de energía interna (luminosidad).

### 4.2 Umbrales de colapso gravitacional

Para el escenario de agujero negro: radio de Schwarzschild R_s = 2GM/c². Si el radio simulado de un objeto cae por debajo de R_s, el objeto se convierte en un sumidero de gravedad con masa fija. En N-body puro esto es simplemente un "sink particle" con radio de accreción.

```python
def schwarzschild_radius(mass):
    G = 6.674e-11
    c = 3e8
    return 2 * G * mass / c**2

# Si R_objeto < k * R_schwarzschild → convertir en sink
```

### 4.3 Regímenes de colisión (mapa de resultados)

Las colisiones planetarias caen en cuatro regímenes según masa y velocidad de impacto:

| Régimen | Condición | Resultado |
|---|---|---|
| **Fusión perfecta** | v < 1.2 v_escape, b < 0.3 | Un cuerpo fusionado |
| **Accreción parcial** | v ~ v_escape, b moderado | Cuerpo grande + escombros |
| **Hit-and-run** | v > 1.5 v_escape, b > 0.5 | Dos cuerpos, masa intercambiada |
| **Erosión / disrupción** | v >> v_escape | Fragmentación, disco de escombros |

Puedes precomputar este mapa con simulaciones de baja resolución (10⁴ partículas) y luego explorar los casos interesantes a alta resolución.

---

## FASE 5 — Visualización y análisis (continuo)

### 5.1 Lectura de snapshots con swiftsimio

```python
import swiftsimio as sw
import matplotlib.pyplot as plt
import numpy as np

data = sw.load("output/snapshot_0050.hdf5")

# Posiciones y materiales
pos = data.gas.coordinates.value
mat_ids = data.gas.material_i_ds.value
mass = data.gas.masses.value

# Colorear por material
# ID 100 = Tillotson iron, 101 = Tillotson basalt, etc.
colors = np.where(mat_ids % 10000 < 100, "gray", "orangered")

fig, ax = plt.subplots(figsize=(10, 10), facecolor="black")
ax.scatter(pos[:, 0], pos[:, 1], s=0.1, c=colors, alpha=0.5)
ax.set_facecolor("black")
plt.savefig("collision_frame.png", dpi=150, bbox_inches="tight")
```

### 5.2 Animación del impacto

```python
import glob
from matplotlib.animation import FuncAnimation

snapshots = sorted(glob.glob("output/snapshot_*.hdf5"))

fig, ax = plt.subplots(figsize=(8, 8), facecolor="black")
scatter = ax.scatter([], [], s=0.1)

def update(frame):
    data = sw.load(snapshots[frame])
    pos = data.gas.coordinates.value
    mat_ids = data.gas.material_i_ds.value
    colors = ["#aaaaaa" if m % 10000 < 100 else "#ff6633" for m in mat_ids]
    scatter.set_offsets(pos[:, :2])
    scatter.set_color(colors)
    return scatter,

ani = FuncAnimation(fig, update, frames=len(snapshots), interval=50)
ani.save("collision.mp4", fps=20, dpi=150)
```

### 5.3 Análisis post-colisión

```python
# Identificar fragmentos post-colisión con DBSCAN o FOF (Friends-of-Friends)
from sklearn.cluster import DBSCAN

# Usar solo partículas ligadas gravitacionalmente
# (energía cinética < energía gravitacional)
def find_bound_fragments(positions, velocities, masses, epsilon=0.1):
    clustering = DBSCAN(eps=epsilon, min_samples=50).fit(positions)
    labels = clustering.labels_
    fragments = []
    for label in set(labels):
        if label == -1: continue  # ruido
        mask = labels == label
        fragments.append({
            "mass": masses[mask].sum(),
            "n_particles": mask.sum(),
            "center": positions[mask].mean(axis=0),
            "velocity": (velocities[mask] * masses[mask, None]).sum(axis=0) / masses[mask].sum()
        })
    return sorted(fragments, key=lambda f: -f["mass"])
```

---

## FASE 6 — Optimizaciones para hardware limitado

### 6.1 Resolución adaptativa

En lugar de resolución uniforme, usa más partículas en el núcleo (alta densidad) y menos en la atmósfera/envuelta. WoMa lo hace automáticamente con su SEAGen cuando usas n_particles ∝ √ρ.

### 6.2 Individual timesteps (block timestepping)

SWIFT usa timesteps individuales por partícula: las partículas en zonas de alta densidad/choque usan pasos pequeños, el resto usa pasos grandes. Esto es automático en SWIFT y es uno de sus mayores ahorros computacionales. Sin esto, un timestep global es 10–100x más lento.

### 6.3 Parámetros de rendimiento en SWIFT

```yaml
Scheduler:
  max_top_level_cells: 32   # reducir si tienes poca RAM
  cell_split_size: 100       # reducir para mejor cache locality

SPH:
  h_min_ratio: 0.1          # evitar partículas con smoothing infinitesimal
```

### 6.4 Reducir resolución solo para exploración

Para encontrar el parámetro de impacto correcto o la velocidad óptima, usa 5000–10000 partículas. Una vez encontrado el escenario interesante, sube a 100k para la simulación definitiva.

---

## FASE 7 — Extensiones y casos especiales

### 7.1 Júpiter vs Júpiter

Usa la EoS CD21_HHe para ambos. El resultado esperado es un objeto con más masa que Júpiter pero aún substelar. Si la masa total supera ~13 M_Jupiter, el resultado es un **enano marrón** (fusión de deuterio, no de hidrógeno). Si supera ~80 M_Jupiter, es una estrella de secuencia principal.

### 7.2 Formación de satélites

Después del impacto, el disco de escombros puede acretar en lunas. SWIFT no hace esto automáticamente (necesitarías N-body de largo plazo acoplado), pero puedes detectar el material en órbita con:

```python
# Material con velocidad orbital > 0 y en disco ≠ cuerpo central
def find_disk_material(pos, vel, M_central, R_central):
    r = np.linalg.norm(pos, axis=1)
    v_escape = np.sqrt(2 * G * M_central / r)
    v_mag = np.linalg.norm(vel, axis=1)
    # Ligado gravitacionalmente pero no en el cuerpo central
    bound = (v_mag < v_escape) & (r > R_central)
    return pos[bound], vel[bound]
```

### 7.3 Choque Tierra-Theia (formación de la Luna)

Este es el caso de validación clásico. Los parámetros canónicos:
- Impactor: ~10% de la masa de la Tierra
- Ángulo: ~45° (b ≈ 0.7)
- Velocidad: ~1.0–1.1 v_escape mutua

El resultado esperado: fusión con disco de escombros de ~2 masas lunares, del cual >70% es material del impactor.

---

## Mapa de decisiones EoS por objeto

| Objeto | Capas | EoS recomendada |
|---|---|---|
| Tierra/rocoso | Hierro + Granito | Til_iron + Til_granite |
| Asteroide | Basalto | Til_basalt |
| Cometa/objeto helado | Hielo de agua | Til_ice o ANEOS_H2O |
| Neptuno/Urano | Hielo + H/He | AQUA + HM80_HHe |
| Júpiter/Saturno | Roca + Hielo + H/He | ANEOS_iron + AQUA + CD21_HHe |
| Enana marrón / protoestrella | H/He | CMS19_H + CMS19_He |
| Estrella (modelo simple) | Gas ideal + presión radiación | EoS propia / ideal_gas |

---

## Referencias y recursos clave

- **SWIFT**: https://www.swiftsim.com — código principal
- **WoMa**: https://github.com/srbonilla/WoMa — condiciones iniciales
- **swiftsimio**: pip install swiftsimio — lectura y visualización
- **ICC Durham Giant Impacts**: https://icc.dur.ac.uk/giant_impacts/ — grupo que desarrolla SWIFT para planetas
- **Kegerreis et al. 2019** (MNRAS 487): paper de referencia para colisiones con SWIFT
- **Ruiz-Bonilla et al. 2020** (MNRAS 500): paper de WoMa
- **pkdgrav3**: https://bitbucket.org/dpotter/pkdgrav3 — alternativa GPU-native

---

## Checklist de progreso

- [ ] Fase 0: Leer sobre SPH, FMM y EoS (conceptual)
- [ ] Fase 1: SWIFT compilado y running en tu máquina
- [ ] Fase 1: WoMa instalado y tutorial.ipynb ejecutado
- [ ] Fase 2: Primer planeta en equilibrio generado con WoMa
- [ ] Fase 2: Condiciones iniciales de impacto creadas
- [ ] Fase 3: Primera simulación corriendo (aunque sea 10k partículas)
- [ ] Fase 3: Primer snapshot visualizado con matplotlib
- [ ] Fase 3: Animación MP4 de la colisión
- [ ] Fase 4: Implementar umbrales de estado (planeta/estrella/BH)
- [ ] Fase 5: Análisis de fragmentos post-impacto
- [ ] Fase 6: Subir resolución a 100k partículas
- [ ] Fase 7: Reproducir caso Tierra-Theia y comparar con literatura



