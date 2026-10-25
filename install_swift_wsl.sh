#!/bin/bash
# Script de instalación de SWIFT en WSL
set -e

echo "=========================================="
echo "  Instalador de SWIFT para WSL"
echo "=========================================="
echo ""

# Actualizar e instalar dependencias
echo "[1/6] Instalando dependencias..."
sudo apt-get update -qq
sudo apt-get install -y -qq libhdf5-dev libomp-dev libtool autoconf automake make g++ git

# Navegar al directorio del proyecto
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

echo ""
echo "[2/6] Directorio del proyecto: $PROJECT_DIR"

# Clonar SWIFT si no existe
if [ ! -d "swiftsim" ]; then
    echo "[3/6] Clonando SWIFT..."
    git clone https://github.com/SWIFTSIM/swiftsim.git --depth 1
else
    echo "[3/6] SWIFT ya clonado"
fi

cd swiftsim

# Configurar y compilar
echo "[4/6] Configurando SWIFT (modo planetario)..."
./autogen.sh 2>/dev/null || true

./configure --with-hydro=planetary \
            --with-equation-of-state=planetary \
            --with-adiabatic-heating=no \
            --with-cooling=no \
            --with-metallicity=no \
            --with-grackle=no \
            --with-fof=no \
            --disable-mpi \
            --disable-vec \
            --enable-omp 2>&1 | tail -20

echo ""
echo "[5/6] Compilando SWIFT (esto tomará varios minutos)..."
make -j$(nproc) 2>&1 | tail -30

echo ""
echo "[6/6] Verificando instalación..."
if [ -f "./swift" ]; then
    echo "[OK] SWIFT compilado exitosamente"
    ./swift --help | head -5
else
    echo "[ERROR] No se encontró el ejecutable swift"
    exit 1
fi

echo ""
echo "=========================================="
echo "  ¡Instalación completada!"
echo "=========================================="
echo ""
echo "Para ejecutar la simulación masiva:"
echo "  cd $PROJECT_DIR"
echo "  ./swiftsim/swift --hydro --self-gravity -t 4 -s swift_config_massive.yml"
echo ""
echo "O usa el script de conveniencia:"
echo "  ./run_swift_wsl.sh"
