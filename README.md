# Astro Collision

Simulación y postproceso de colisiones planetarias rocosas basada en `WoMa` para condiciones iniciales y compatible con salidas simples HDF5 o salidas tipo SWIFT/WoMa.

## Qué revisé y qué estaba mal

La versión original tenía varios problemas que afectaban tanto a la validez física como a la usabilidad:

- **Rutas hardcodeadas de Linux**
  - Los scripts no eran portables y no funcionaban en tu entorno Windows.

- **Planeta objetivo demasiado simplificado**
  - Se generaba una Tierra de una sola capa con un único material.
  - Para impactos rocosos esto es peor que usar un cuerpo diferenciado con núcleo metálico y manto silicatado.

- **Impactor generado por simple escalado geométrico**
  - Se clonaba el target y luego se escalaban posiciones y masas.
  - Eso no es una construcción hidrostática consistente del impactor.

- **Dependencia dura de `swiftsimio`**
  - No estaba instalado en el entorno.
  - Además, los snapshots encontrados en `simulation_output/` no son del formato que asumía ese código.

- **Visualización poco eficiente**
  - La animación usaba scatter 3D y precargaba todo en memoria.
  - Para este tipo de datos, una proyección 2D con muestreo fijo suele ser mucho más rápida y estable.

- **Configuración de salida inconsistente**
  - El `swift_config.yml` escribía en un directorio y con un patrón de nombres distinto del que usan ahora las herramientas de visualización.

## Qué implementé

- **Modelo rocoso diferenciado**
  - Núcleo de `Til_iron` y manto de `Til_granite`.
  - Construcción hidrostática con `WoMa`.

- **Generación física independiente del target y del impactor**
  - Ahora ambos cuerpos se generan por separado.
  - Se evita el escalado artificial del target.

- **Impacto configurado con velocidad de escape mutua**
  - La velocidad se calcula en SI usando:
  - `v_esc = sqrt(2 G (M_t + M_i) / (R_t + R_i))`

- **Sistema centrado en el centro de masas**
  - Las condiciones iniciales quedan en el frame del centro de masas.

- **Mejor reparto de partículas**
  - Si no indicas el número de partículas del impactor, se calcula para mantener aproximadamente la misma masa por partícula que en el target.

- **Lectura robusta de snapshots**
  - Soporta:
  - archivos simples con datasets raíz `position`, `velocity`, `mass`, `material`
  - archivos tipo SWIFT/WoMa con `PartType0`, `Header` y `Units`

- **Visualización y animación optimizadas**
  - Sin dependencia de `swiftsimio`
  - Soporte para `xy`, `xz`, `yz`
  - Muestreo de partículas configurable
  - Animación 2D más rápida y con menos memoria

- **Configuración SWIFT más coherente**
  - Salida en `simulation_output/`
  - nombres `snapshot_*.hdf5`
  - `dt_max` más conservador

## Estructura del proyecto

- `generate_earth.py`
  - Genera un planeta rocoso diferenciado aislado.

- `generate_impact.py`
  - Genera las condiciones iniciales de impacto target-impactor.

- `planetary_utils.py`
  - Utilidades físicas y de lectura/escritura HDF5.

- `visualize.py`
  - Render de snapshots a PNG.

- `animate.py`
  - Genera GIF o MP4 a partir de snapshots.

- `swift_config.yml`
  - Configuración base para una corrida tipo SWIFT.

## Instalación

En tu entorno virtual:

```powershell
.\venv\Scripts\pip install -r requirements.txt
```

## Notas sobre Windows

- `WoMa`, `numpy`, `scipy`, `h5py` y `matplotlib` deberían funcionar bien en Windows.
- `PySPH` te falló porque necesita **Microsoft Visual C++ Build Tools** para compilar dependencias nativas.
- Para este repositorio, **ya no hace falta `swiftsimio`** para visualizar snapshots.
- Si quieres ejecutar **SWIFT** de forma seria, lo más práctico suele ser **WSL2 o Linux nativo**.

## Uso

### 1. Generar un planeta tipo Tierra

```powershell
.\venv\Scripts\python generate_earth.py --particles 20000 --output earth_IC.hdf5
```

### 2. Generar una colisión tipo Tierra-Theia

Ejemplo con impactor del 10% de la masa terrestre, ángulo de 45° y velocidad de 1.1 veces la de escape mutua:

```powershell
.\venv\Scripts\python generate_impact.py --target-mass 1.0 --impactor-mass-ratio 0.1 --impact-angle 45 --velocity-escape 1.1 --target-particles 40000 --output impact_IC.hdf5
```

También puedes guardar los cuerpos por separado:

```powershell
.\venv\Scripts\python generate_impact.py --target-output target_IC.hdf5 --impactor-output impactor_IC.hdf5
```

### 3. Visualizar el último snapshot

```powershell
.\venv\Scripts\python visualize.py
```

### 4. Visualizar todos los snapshots

```powershell
.\venv\Scripts\python visualize.py --all --color-by speed --projection xz --max-particles 20000
```

### 5. Crear una animación

```powershell
.\venv\Scripts\python animate.py --output collision_animation.gif --projection xy --color-by material --max-particles 15000
```

Para MP4:

```powershell
.\venv\Scripts\python animate.py --output collision_animation.mp4
```

## Si vas a usar SWIFT

Si tienes un binario funcional de SWIFT con hidro planetaria, la idea de flujo es:

1. Generar `impact_IC.hdf5`
2. Lanzar SWIFT con `swift_config.yml`
3. Leer los snapshots generados en `simulation_output/`
4. Renderizar o animar con `visualize.py` y `animate.py`

## Consejos de rendimiento

- **Usa proyección 2D**
  - Es mucho más rápida que scatter 3D en matplotlib.

- **Limita partículas visibles**
  - `--max-particles 10000` o `15000` suele ser suficiente para previsualización.

- **Usa `--skip` en animación**
  - Reduce mucho el tiempo de exportación.

- **Para SWIFT, aprovecha CPU multinúcleo**
  - Si tu build de SWIFT soporta hilos, usa todos los cores razonables de tu equipo.

- **GPU**
  - En este proyecto, la visualización Python actual no usa GPU.
  - La mejor mejora real de rendimiento no está en matplotlib, sino en el solver físico.
  - Si quieres acelerar de verdad la simulación, lo ideal es:
    - SWIFT bien compilado con paralelismo CPU
    - Linux/WSL2
    - o una ruta específica con solver/SPH que soporte GPU de forma madura

## Limitaciones científicas actuales

Esto ahora está bastante mejor, pero todavía hay límites importantes:

- **No sustituye una simulación planetaria publicable**
  - Para eso necesitas SWIFT planetario bien configurado, relajación previa de cada cuerpo y validación de convergencia con resolución.

- **Sin relajación previa explícita**
  - Lo recomendable es relajar cada planeta antes del impacto para reducir ruido numérico inicial.

- **EoS simplificada**
  - Se usan materiales Tillotson rocosos, adecuados para exploración, pero no equivalen a una campaña seria con tablas ANEOS/SESAME calibradas.

- **Sin física avanzada**
  - No hay material strength, radiación, química de vapor, ni tratamiento detallado de atmósferas o gigantes gaseosos.

## Recomendación práctica

Si tu objetivo es una simulación visualmente convincente y razonablemente física en un PC normal:

- usa `WoMa` para generar ICs
- usa SWIFT planetario si lo tienes disponible
- trabaja primero con `2e4` a `1e5` partículas
- renderiza en 2D con subsampling
- valida varias configuraciones de ángulo, relación de masas y velocidad de impacto

Si quieres, en el siguiente paso te puedo dejar también:

- un script de lanzamiento de corrida para Windows/WSL
- una rutina de análisis de energía, momento angular y fragmentos
- o una versión de visualización más bonita con mapas de densidad en lugar de puntos
