#!/bin/bash
# Script de instalación de SWIFT en WSL - Versión corregida
set -e

echo "=========================================="
echo "  Instalador de SWIFT para WSL"
echo "=========================================="
echo ""

# Navegar al directorio del proyecto
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

echo "Directorio del proyecto: $PROJECT_DIR"
echo ""

# Actualizar e instalar dependencias
echo "[1/6] Instalando dependencias..."
sudo apt-get update -qq
sudo apt-get install -y -qq libhdf5-dev libomp-dev libtool autoconf automake make g++ git

# Clonar SWIFT si no existe
if [ ! -d "swiftsim" ]; then
    echo ""
    echo "[2/6] Clonando SWIFT..."
    git clone https://github.com/SWIFTSIM/swiftsim.git --depth 1
else
    echo ""
    echo "[2/6] SWIFT ya clonado"
fi

cd swiftsim

# Ejecutar autogen.sh
echo ""
echo "[3/6] Ejecutando autogen.sh..."
./autogen.sh

# Configurar SWIFT
echo ""
echo "[4/6] Configurando SWIFT (modo planetario)..."
./configure \
    --with-hydro=planetary \
    --with-equation-of-state=planetary \
    --disable-adiabatic-heating \
    --disable-cooling \
    --disable-metallicity \
    --disable-grackle \
    --disable-fof \
    --disable-mpi \
    --disable-vec \
    --enable-omp

# Verificar que se creó el Makefile
if [ ! -f "Makefile" ]; then
    echo ""
    echo "[ERROR] No se generó el Makefile. El configure falló."
    echo "Revisar el error arriba."
    exit 1
fi

echo ""
echo "[5/6] Compilando SWIFT (esto tomará varios minutos)..."
make -j$(nproc)

echo ""
echo "[6/6] Verificando instalación..."
if [ -f "./swift" ]; then
    echo "[OK] SWIFT compilado exitosamente"
    echo ""
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
