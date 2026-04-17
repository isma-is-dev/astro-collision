#!/bin/bash
# Ejecutar simulación cinematográfica con MILES de snapshots

cd "$(dirname "$0")"

echo "=========================================="
echo "  Simulación CINEMATOGRÁFICA"
echo "=========================================="
echo ""
echo "Configuración:"
echo "  - 5,000 snapshots (uno cada 2 segundos de simulación)"
echo "  - Duración: ~2.7 horas de simulación física"
echo "  - Animación resultante: ~3 minutos a 30 FPS"
echo ""

# Crear directorio
mkdir -p cinematic_output

# Verificar espacio disponible
AVAILABLE=$(df -h . | tail -1 | awk '{print $4}')
echo "Espacio disponible: $AVAILABLE"
echo "Estimación: ~5GB necesarios para 5,000 snapshots"
echo ""

read -p "¿Continuar? (s/n): " confirm
if [[ $confirm != [sS] ]]; then
    echo "Cancelado"
    exit 0
fi

echo ""
echo "Iniciando simulación..."
echo "(Esta simulación tomará varias horas en completarse)"
echo ""

# Ejecutar SWIFT
./swiftsim/swift --hydro --self-gravity -t 4 -s swift_config_cinematic.yml 2>&1 | tee cinematic_simulation.log

echo ""
echo "=========================================="
echo "  Simulación completada"
echo "=========================================="
echo ""
echo "Generando animación..."
echo ""

# Contar snapshots
SNAPSHOT_COUNT=$(ls cinematic_output/frame_*.hdf5 2>/dev/null | wc -l)
echo "Snapshots generados: $SNAPSHOT_COUNT"

if [ $SNAPSHOT_COUNT -gt 0 ]; then
    echo ""
    echo "Para crear la animación ejecuta:"
    echo "  python animate.py --snapshot-dir cinematic_output --output collision_movie.mp4 --fps 30 --projection xy"
    echo ""
    echo "Estimación de duración del video:"
    DURATION=$((SNAPSHOT_COUNT / 30))
    echo "  ~${DURATION} segundos a 30 FPS"
    echo "  ~$((DURATION / 60)) minutos"
fi

echo ""
echo "Snapshots en: cinematic_output/"
ls -lh cinematic_output/ | tail -5
