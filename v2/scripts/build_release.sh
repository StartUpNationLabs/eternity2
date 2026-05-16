#!/bin/bash
# Vol-107 T3 — release build with PGO for the production binaries.
#
# Usage: scripts/build_release.sh
#
# Produces (under target/release/):
#   bf_bw         — Blackwood backtracker, PGO-optimized.
#                   Use `E2_BF_UNROLLED_V17A_CONST=1` for the fastest
#                   variant (84-85M nps on canonical, +35% over baseline).
#   vanilla_v2    — Vanilla DFS variant, PGO-optimized.
#                   97 M pp/s on canonical, +30% over vanilla_fastest.
#   bf_similarity — Pairwise board similarity for cross-thread analysis.
#
# Training workload: each bin is profiled on canonical Selby-Riordan 16x16
# for ~8s at typical operational settings, then rebuilt with the captured
# profile data.
#
# Prerequisite: Homebrew llvm (`brew install llvm`); set LLVM_PROFDATA
# if your install path differs.

set -euo pipefail

echo "=== vol-107 T3 release build with PGO ==="
echo

scripts/build_pgo.sh eternity2-blackwood-fast bf_bw \
    --schedule v17a --threads 1 --budget-ms 8000

echo
scripts/build_pgo.sh eternity2-blackwood-fast vanilla_v2 \
    --budget-ms 8000

echo
# bf_similarity is a measurement bin, less performance-critical;
# regular release build is fine.
source "$HOME/.cargo/env"
cargo build --release -p eternity2-blackwood-fast --bin bf_similarity

echo
echo "=== summary ==="
echo "Binaries:"
ls -lh target/release/{bf_bw,vanilla_v2,bf_similarity} 2>/dev/null

echo
echo "Quick sanity check (single-thread 5s on canonical):"
echo "  bf_bw (E2_BF_UNROLLED_V17A_CONST=1):"
E2_BF_UNROLLED_V17A_CONST=1 ./target/release/bf_bw --schedule v17a --threads 1 --budget-ms 5000 2>&1 | tail -1
echo "  vanilla_v2:"
./target/release/vanilla_v2 --budget-ms 5000 2>&1 | tail -1
