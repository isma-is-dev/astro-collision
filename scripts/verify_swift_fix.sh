#!/bin/bash
# Quick verification that the rebuilt SWIFT runs on our existing earth_IC.hdf5
# without segfaulting. Expected outcome: many snapshots in settle_earth_output/.
# Usage: wsl.exe bash scripts/verify_swift_fix.sh
set -u

cd /mnt/c/Users/atton/Desktop/Code/astro-collision

echo "== SWIFT binary info =="
ls -la swiftsim/swift
file swiftsim/swift | head -1

echo "== Preparing output dir =="
rm -rf settle_earth_output
mkdir -p settle_earth_output

echo "== Running short settle (up to ~4000 s simulated, snapshots every 200 s) =="
set +e
./swiftsim/swift --hydro --self-gravity -t 2 \
  -s /mnt/c/Users/atton/Desktop/Code/astro-collision/swift_config_settle_earth.yml \
  > settle_earth.log 2>&1
rc=$?
set -e

echo "== Exit code: $rc =="
echo "== Last lines of log =="
tail -n 12 settle_earth.log

echo "== Snapshots produced =="
ls -1 settle_earth_output/ | grep -E '\.hdf5$' | sort
count=$(ls -1 settle_earth_output/ | grep -cE '\.hdf5$' || true)
echo "Snapshot count: $count"

if [ "$rc" -eq 0 ] && [ "$count" -gt 1 ]; then
  echo "RESULT: OK - SWIFT completed and produced multiple snapshots."
else
  echo "RESULT: STILL BROKEN - check settle_earth.log for details."
fi
