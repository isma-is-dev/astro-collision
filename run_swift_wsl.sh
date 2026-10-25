#!/bin/bash
# Script para ejecutar simulación masiva en WSL
set -e

cd "$(dirname "$0")"

# Verificar que existe SWIFT
if [ ! -f "swiftsim/swift" ]; then
    echo "[ERROR] SWIFT no encontrado. Ejecuta primero: ./install_swift_wsl.sh"
    exit 1
fi

# Verificar archivos necesarios
if [ ! -f "massive_impact_IC.hdf5" ]; then
    echo "[ERROR] No se encontró massive_impact_IC.hdf5"
    exit 1
fi

if [ ! -f "swift_config_massive.yml" ]; then
    echo "[ERROR] No se encontró swift_config_massive.yml"
    exit 1
fi

# Crear directorio de salida
mkdir -p massive_simulation_output

echo "=========================================="
echo "  Ejecutando Simulación Masiva"
echo "=========================================="
echo ""
echo "Configuración:"
echo "  - Target: 3 M⊕ (super-Tierra)"
echo "  - Impactor: 2 M⊕"
echo "  - Partículas: ~98,000"
echo "  - Duración: ~28 horas de simulación física"
echo "  - Snapshots: cada 30 minutos"
echo ""
echo "Comando:"
echo "  ./swiftsim/swift --hydro --self-gravity -t 4 -s swift_config_massive.yml"
echo ""
echo "Presiona Ctrl+C para detener la simulación"
echo "Iniciando en 3 segundos..."
sleep 3

# Ejecutar SWIFT
./swiftsim/swift --hydro --self-gravity -t 4 -s swift_config_massive.yml

echo ""
echo "=========================================="
echo "  Simulación completada o detenida"
echo "=========================================="
echo ""
echo "Resultados en: massive_simulation_output/"
echo "Para visualizar: python visualize.py --snapshot-dir massive_simulation_output"
echo "Para animar: python animate.py --snapshot-dir massive_simulation_output --output massive_collision.mp4"
