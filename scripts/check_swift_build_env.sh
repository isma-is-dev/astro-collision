#!/bin/bash
set -u
cd /mnt/c/Users/atton/Desktop/Code/astro-collision
echo "== gcc =="
gcc --version | head -1
echo "== packages =="
for p in libhdf5-dev libgsl-dev libfftw3-dev autoconf automake libtool pkg-config libmetis-dev libnuma-dev make build-essential; do
  if dpkg -s "$p" >/dev/null 2>&1; then
    echo "OK  $p"
  else
    echo "--  $p (missing)"
  fi
done
echo "== swiftsim status =="
if [ -f swiftsim/config.status ]; then
  echo "config.status exists"
  grep -E "^#\s*\.?/configure|CFLAGS" swiftsim/config.status | head -5
else
  echo "no config.status yet"
fi
if [ -f swiftsim/Makefile ]; then
  echo "Makefile exists (already configured once)"
fi
echo "== current binary info =="
if [ -f swiftsim/swift ]; then
  stat -c "swift: %s bytes, modified %y" swiftsim/swift
fi
