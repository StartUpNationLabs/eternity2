#!/usr/bin/env bash
# Strain-cascade diagnostic: drop the asymmetric hint (7,8) and run
# unconstrained PT for 600s. If the score breaks above 449, the
# asymmetric hint IS the structural origin of the plateau.
#
# This is NOT an "official E2" claim — official E2 has 5 hints — but
# is a clean diagnostic for the strain-cascade hypothesis from
# vol-5 notes.
#
# Usage: scripts/strain_diagnostic.sh
# Runs in the foreground; expect ~10 min.

set -uo pipefail
cd "$(dirname "$0")/.."

LOG=/tmp/strain_diagnostic.log

echo "=== STRAIN DIAGNOSTIC start: $(date) ==="
echo "Running PT with --pin-hints false: ALL 5 hints unpinned."
echo "(That's stronger than just unpinning (7,8) but reveals the"
echo "upper ceiling of constrained-on-only-corners structure.)"
echo

./target/release/pt_e2 \
    --pt-seconds 600 \
    --cp-seconds 60 \
    --skip-sa-compare \
    --pin-hints false \
    --seed 3806637746 \
    2>&1 | tee "$LOG"

echo
echo "=== STRAIN DIAGNOSTIC end: $(date) ==="
grep -E "PT:|matched_edges" "$LOG" | head -5
