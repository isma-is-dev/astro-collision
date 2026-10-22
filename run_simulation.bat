@echo off
chcp 65001 >nul
echo ==========================================
echo   Simulación de Impacto Masivo
echo ==========================================
echo.
echo Configuración:
echo   - Target: 3 M⊕ (super-Tierra)
echo   - Impactor: 2 M⊕
echo   - Partículas: ~98,000
echo   - Duración: ~28 horas de simulación física
echo   - Snapshots: cada 30 minutos
echo.

REM Crear directorio de salida
if not exist "massive_simulation_output" mkdir massive_simulation_output

echo Intentando ejecutar SWIFT...
echo.

REM Verificar si swift existe
where swift >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] SWIFT encontrado en el PATH
    echo Ejecutando simulación...
    echo Comando: swift --hydro --self-gravity -t 4 -s swift_config_massive.yml
    echo.
    swift --hydro --self-gravity -t 4 -s swift_config_massive.yml
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ==========================================
        echo   ¡Simulación completada!
        echo ==========================================
        echo.
        echo Resultados en: massive_simulation_output/
        echo Para visualizar: python visualize.py --snapshot-dir massive_simulation_output
        echo Para animar: python animate.py --snapshot-dir massive_simulation_output --output massive_collision.mp4
    ) else (
        echo.
        echo [ERROR] SWIFT terminó con código de error: %ERRORLEVEL%
    )
) else (
    echo [ERROR] SWIFT no encontrado en el PATH
    echo.
    echo ==========================================
    echo   INSTRUCCIONES PARA EJECUTAR
    echo ==========================================
    echo.
    echo Opción 1 - WSL (Recomendado):
    echo   1. Abrir WSL: wsl
    echo   2. cd /mnt/c/Users/atton/Desktop/Code/astro-collision
    echo   3. Instalar dependencias: sudo apt update ; sudo apt install -y libhdf5-dev libomp-dev
    echo   4. Clonar SWIFT: git clone https://github.com/SWIFTSIM/swiftsim.git
    echo   5. Compilar: cd swiftsim ; ./autogen.sh ; ./configure --with-hydro=planetary --with-equation-of-state=planetary ; make -j4
    echo   6. Ejecutar: ./swift --hydro --self-gravity -t 4 -s ../swift_config_massive.yml
    echo.
    echo Opción 2 - Docker:
    echo   docker run -v %%CD%%:/work -w /work swiftplanetary/swift:latest swift --hydro --self-gravity -t 4 -s swift_config_massive.yml
    echo.
    echo Archivos generados:
    echo   - massive_impact_IC.hdf5 (condiciones iniciales)
    echo   - swift_config_massive.yml (configuración SWIFT)
    echo.
)

pause
