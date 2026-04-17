#!/bin/bash
# Ejecutar simulación con output en tiempo real

cd "$(dirname "$0")"

echo "=========================================="
echo "  Ejecutando Simulación de Impacto"
echo "=========================================="
echo ""
echo "Archivo: impact_IC.hdf5 (1 M⊕ vs 0.1 M⊕, ~48k partículas)"
echo "Config: swift_config.yml"
echo ""
echo "Iniciando SWIFT..."
echo "(Presiona Ctrl+C para detener)"
echo ""

# Ejecutar con output en tiempo real a terminal y a log
./swiftsim/swift --hydro --self-gravity -t 2 -s swift_config.yml 2>&1 | tee live_simulation.log

echo ""
echo "=========================================="
echo "  Simulación completada"
echo "=========================================="
echo ""
echo "Snapshots en: simulation_output/"
echo "Log guardado en: live_simulation.log"
echo ""
ls -lh simulation_output/
