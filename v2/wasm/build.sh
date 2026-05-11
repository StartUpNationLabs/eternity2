#!/usr/bin/env bash
# Build the WASM bundle for the educational frontend.
# Requirements: cargo, wasm-pack, system wasm-opt (e.g. `brew install binaryen`).
set -euo pipefail
cd "$(dirname "$0")"

# Ensure cargo/wasm-pack from the standard rustup install path are reachable
# in non-login shells.
export PATH="$HOME/.cargo/bin:$PATH"

wasm-pack build --target web --out-dir pkg --release

# wasm-pack 0.14 ships an outdated wasm-opt; run system wasm-opt instead.
if command -v wasm-opt >/dev/null 2>&1; then
    # --enable-* flags match what current rustc emits; without them wasm-opt
    # rejects valid modules. Mutable globals, NT-FP, sign-ext, ref-types,
    # multivalue, bulk-memory are all baseline since Rust 1.82.
    wasm-opt \
        --enable-mutable-globals \
        --enable-nontrapping-float-to-int \
        --enable-sign-ext \
        --enable-reference-types \
        --enable-multivalue \
        --enable-bulk-memory \
        -O3 pkg/eternity2_wasm_bg.wasm -o pkg/eternity2_wasm_bg.wasm.tmp
    mv pkg/eternity2_wasm_bg.wasm.tmp pkg/eternity2_wasm_bg.wasm
    echo "optimized: $(wc -c < pkg/eternity2_wasm_bg.wasm) bytes"
else
    echo "skipping wasm-opt (not on PATH)"
fi
