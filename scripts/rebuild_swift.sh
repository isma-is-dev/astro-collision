#!/bin/bash
# Rebuild SWIFT inside WSL with safe flags (no -march=amdfam10, no -ffast-math).
# Usage: wsl.exe bash scripts/rebuild_swift.sh
set -euo pipefail

cd /mnt/c/Users/atton/Desktop/Code/astro-collision/swiftsim

echo "== Cleaning previous build =="
make distclean >/dev/null 2>&1 || true

echo "== Regenerating autotools =="
./autogen.sh

echo "== Configuring with SAFE flags =="
# IMPORTANT: --disable-optimization is what actually removes the suspect flags.
# SWIFT's AX_CC_MAXOPT m4 macro is the one that appends -ffast-math, -funroll-loops,
# -fstrict-aliasing and -march=amdfam10 AFTER any user CFLAGS, so passing only
# CFLAGS=... at configure time does NOT override them. --disable-optimization
# skips both AX_CC_MAXOPT and AX_EXT (which adds -mavx512vbmi).
#
# We still want a reasonable -O2 for speed, which we set via CFLAGS.
./configure \
  --disable-optimization \
  --with-hydro=planetary \
  --with-equation-of-state=planetary \
  --disable-adiabatic-heating \
  --disable-cooling \
  --disable-metallicity \
  --disable-grackle \
  --disable-fof \
  --disable-mpi \
  --disable-vec \
  --disable-hand-vec \
  --disable-ipo \
  --enable-omp \
  --enable-debugging-checks \
  CFLAGS='-O1 -g -pthread -fno-omit-frame-pointer'

echo "== CFLAGS sanity check =="
effective_cflags=$(grep -m1 '^CFLAGS ' Makefile | sed 's/^CFLAGS = //')
echo "Effective CFLAGS: $effective_cflags"
bad=""
for flag in -ffast-math -march=amdfam10 -mavx512vbmi -funroll-loops; do
  if echo " $effective_cflags " | grep -q " $flag "; then
    bad="$bad $flag"
  fi
done
if [ -n "$bad" ]; then
  echo "ERROR: build would still use suspect flags:$bad"
  echo "Aborting before make. Please inspect configure.ac / m4/ax_cc_maxopt.m4."
  exit 1
fi
echo "OK: no suspect flags in CFLAGS."

echo "== Building =="
make -j"$(nproc)"

echo "== Build done =="
ls -la swift
./swift --help 2>&1 | head -n 6 || true
