#!/bin/bash
# Profile-guided build for a bin in this workspace.
#
# Usage:
#   scripts/build_pgo.sh <crate> <bin> [training-args...]
#
# Example (canonical Selby-Riordan E2, 8s training):
#   scripts/build_pgo.sh eternity2-blackwood-fast bf_bw \
#       --schedule v17a --threads 1 --budget-ms 8000
#
# Result: the PGO-optimized binary at `target/release/<bin>`.
#
# Workflow per [rustc PGO docs](https://doc.rust-lang.org/rustc/profile-guided-optimization.html):
#   1. Build instrumented binary (RUSTFLAGS=-Cprofile-generate=...).
#   2. Run instrumented binary on representative workload.
#   3. Merge .profraw → .profdata (needs Homebrew llvm-profdata, not Xcode's
#      since Xcode's is version-mismatched against Rust's instrumentation).
#   4. Rebuild with RUSTFLAGS=-Cprofile-use=...
#
# Vol-106 measurement (canonical Selby-Riordan, single-thread):
#   bf_bw:          63 M nps -> 72 M nps  (+14%)
#   vanilla_v2:     93 M pps -> 97 M pps  (+4%)
#   vanilla_fastest: 73 M pps -> 82 M pps  (+12%)

set -euo pipefail

CRATE="${1:?usage: build_pgo.sh <crate> <bin> [training-args...]}"
BIN="${2:?usage: build_pgo.sh <crate> <bin> [training-args...]}"
shift 2

PROFDIR="/tmp/pgo-${BIN}"
LLVM_PROFDATA="${LLVM_PROFDATA:-/opt/homebrew/opt/llvm/bin/llvm-profdata}"

if [ ! -x "$LLVM_PROFDATA" ]; then
    echo "ERROR: $LLVM_PROFDATA not found. Install via: brew install llvm" >&2
    exit 1
fi

source "$HOME/.cargo/env"

echo "[pgo] step 1: instrumented build → $PROFDIR"
rm -rf "$PROFDIR"
mkdir -p "$PROFDIR"
RUSTFLAGS="-Cprofile-generate=$PROFDIR" cargo build --release -p "$CRATE" --bin "$BIN"

echo "[pgo] step 2: training run with args: $*"
./target/release/"$BIN" "$@" > /dev/null

echo "[pgo] step 3: merge .profraw → merged.profdata"
"$LLVM_PROFDATA" merge -o "$PROFDIR/merged.profdata" "$PROFDIR"
ls -la "$PROFDIR/merged.profdata"

echo "[pgo] step 4: PGO-optimized rebuild"
# Touch a source file to force the bin to recompile under new RUSTFLAGS.
SRC="$(find crates/"${CRATE#eternity2-}"/src -name '*.rs' -print -quit)"
touch "$SRC"
RUSTFLAGS="-Cprofile-use=$PROFDIR/merged.profdata" cargo build --release -p "$CRATE" --bin "$BIN"

echo "[pgo] done. Binary at target/release/$BIN"
