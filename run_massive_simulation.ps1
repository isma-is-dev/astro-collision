# Script para ejecutar simulación masiva de impacto planetario
# Requiere SWIFT instalado (ver instrucciones abajo)

param(
    [string]$SwiftExe = "swift",
    [int]$Threads = 4,
    [string]$Config = "swift_config_massive.yml"
)

$OutputDir = "massive_simulation_output"

# Crear directorio de salida si no existe
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
    Write-Host "Creado directorio: $OutputDir" -ForegroundColor Green
}

# Verificar que existen los archivos necesarios
$RequiredFiles = @("massive_impact_IC.hdf5", $Config)
foreach ($file in $RequiredFiles) {
    if (!(Test-Path $file)) {
        Write-Error "Archivo requerido no encontrado: $file"
        exit 1
    }
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Simulación de Impacto Masivo" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuración:" -ForegroundColor Yellow
Write-Host "  - Target: 3 M⊕ (super-Tierra)"
Write-Host "  - Impactor: 2 M⊕"
Write-Host "  - Partículas: ~98,000"
Write-Host "  - Duración: ~28 horas de simulación física"
Write-Host "  - Snapshots: cada 30 minutos"
Write-Host ""
Write-Host "Comando a ejecutar:" -ForegroundColor Yellow
Write-Host "  $SwiftExe --hydro --self-gravity -t $Threads -s $Config" -ForegroundColor Green
Write-Host ""

# Intentar ejecutar SWIFT
try {
    & $SwiftExe --hydro --self-gravity -t $Threads -s $Config 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Green
        Write-Host "  ¡Simulación completada!" -ForegroundColor Green
        Write-Host "==========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Resultados en: $OutputDir/" -ForegroundColor Yellow
        Write-Host "Para visualizar: python visualize.py --snapshot-dir $OutputDir" -ForegroundColor Yellow
        Write-Host "Para animar: python animate.py --snapshot-dir $OutputDir --output massive_collision.mp4" -ForegroundColor Yellow
    } else {
        throw "SWIFT terminó con código de error: $LASTEXITCODE"
    }
}
catch {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "  ERROR: No se pudo ejecutar SWIFT" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Mensaje de error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "INSTRUCCIONES DE INSTALACIÓN:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Opción 1 - Windows Subsystem for Linux (WSL):" -ForegroundColor Cyan
    Write-Host "  1. Abrir WSL: wsl" -ForegroundColor White
    Write-Host "  2. Navegar al proyecto: cd /mnt/c/Users/atton/Desktop/Code/astro-collision" -ForegroundColor White
    Write-Host "  3. Instalar dependencias: sudo apt update; sudo apt install -y libhdf5-dev libomp-dev" -ForegroundColor White
    Write-Host "  4. Clonar SWIFT: git clone https://github.com/SWIFTSIM/swiftsim.git" -ForegroundColor White
    Write-Host "  5. Compilar: cd swiftsim; ./autogen.sh; ./configure --with-hydro=planetary --with-equation-of-state=planetary" -ForegroundColor White
    Write-Host "  6. Ejecutar: ./swift --hydro --self-gravity -t 4 -s ../swift_config_massive.yml" -ForegroundColor White
    Write-Host ""
    Write-Host "Opción 2 - Docker:" -ForegroundColor Cyan
    Write-Host "  docker run -v ${PWD}:/work -w /work swiftplanetary/swift:latest" -ForegroundColor White
    Write-Host "    swift --hydro --self-gravity -t 4 -s swift_config_massive.yml" -ForegroundColor White
    Write-Host ""
    Write-Host "Para mas detalles, ver README.md seccion Installation" -ForegroundColor Yellow
}
