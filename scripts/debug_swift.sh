#!/bin/bash
# Run SWIFT under gdb with batch mode to capture an exact backtrace
# of the crash. The binary already carries debug info (-g), so symbols
# should resolve cleanly.
#
# Usage: wsl.exe bash scripts/debug_swift.sh

set -u

cd /mnt/c/Users/atton/Desktop/Code/astro-collision

if ! command -v gdb >/dev/null 2>&1; then
  echo "gdb is not installed. Install it with:"
  echo "  sudo apt-get install -y gdb"
  exit 2
fi

rm -rf settle_earth_output
mkdir -p settle_earth_output

echo "== Running SWIFT under gdb (single thread, planetary settle) =="
echo "== This may take ~10 seconds; it will crash and print a backtrace =="
gdb -batch \
    -ex 'set pagination off' \
    -ex 'set print thread-events off' \
    -ex 'run --hydro --self-gravity -t 1 -s /mnt/c/Users/atton/Desktop/Code/astro-collision/swift_config_settle_earth.yml' \
    -ex 'echo \n===== BACKTRACE (crashing thread) =====\n' \
    -ex 'bt 40' \
    -ex 'echo \n===== FULL BACKTRACE =====\n' \
    -ex 'bt full' \
    -ex 'echo \n===== THREAD LIST =====\n' \
    -ex 'info threads' \
    -ex 'echo \n===== BACKTRACE ALL THREADS =====\n' \
    -ex 'thread apply all bt 20' \
    -ex 'quit' \
    ./swiftsim/swift 2>&1 | tee gdb_swift.log

echo
echo "== Summary =="
grep -n -E 'Program received|Segmentation fault|^#[0-9]|\(gdb\)' gdb_swift.log | head -n 40 || true
