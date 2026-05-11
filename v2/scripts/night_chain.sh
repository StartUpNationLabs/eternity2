#!/usr/bin/env bash
# Night autopilot: after NE2.1 sweep finishes, run NE1 funnel + NE2-iter
# in sequence. Logs to /tmp/night_chain.log.
#
# Phase 1: wait for ne2_1_inner_sweep.sh to finish (or already done).
# Phase 2: run NE1 frame-first top-6 funnel (~1.9h).
# Phase 3: run NE2-iter iterative-deepen (~30 min).
# Phase 4: end. Morning-user sees committed results.

set -uo pipefail  # do NOT set -e — we want to continue past errors

cd "$(dirname "$0")/.."
LOG=/tmp/night_chain.log
echo "===== NIGHT CHAIN start: $(date) =====" | tee "$LOG"

# Phase 1 — wait for any running ne2_1_inner_sweep.sh
echo
echo "PHASE 1: waiting for NE2.1 sweep to finish..." | tee -a "$LOG"
while pgrep -lf 'ne2_1_inner_sweep' >/dev/null; do
    sleep 30
done
echo "PHASE 1 done: $(date)" | tee -a "$LOG"

# Brief pause to settle.
sleep 5

# Phase 2 — NE1 funnel.
echo
echo "PHASE 2: NE1 frame-first top-6 funnel  $(date)" | tee -a "$LOG"
bash scripts/ne1_top6_funnel.sh 2>&1 | tee -a "$LOG"
echo "PHASE 2 done: $(date)" | tee -a "$LOG"

# Commit any results.
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
git add -A output/ne1_*.json output/frame_first_e2_*.json output/frame_first_e2_*.url.txt 2>/dev/null || true

# Phase 3 — NE2-iter.
echo
echo "PHASE 3: NE2 iterative-deepen  $(date)" | tee -a "$LOG"
bash scripts/ne2_iterative_deepen.sh 3 600 2>&1 | tee -a "$LOG"
echo "PHASE 3 done: $(date)" | tee -a "$LOG"

git add -A output/ne2_iter_*.json output/pt_e2_*.json 2>/dev/null || true

echo
echo "===== NIGHT CHAIN end: $(date) =====" | tee -a "$LOG"
