#!/usr/bin/env bash
# Assemble full vol-119 basin corpus into a single dir for MIP use.

set -e
cd "$(dirname "$0")/.."

TS="$(date +%Y%m%dT%H%M%S)"
CORPUS_DIR="output/vol-119/corpus_full_${TS}"
mkdir -p "$CORPUS_DIR"

# Originals
cp output/vol-110/basins/bseed1_score459.json "$CORPUS_DIR/cluster_A_bseed1.json"
cp output/vol-110/basins/bseed6_score459.json "$CORPUS_DIR/cluster_A_bseed6.json"
cp output/vol-110/basins/bseed11_score459.json "$CORPUS_DIR/cluster_A_bseed11.json"
cp output/vol-110/basins/orig_score459.json "$CORPUS_DIR/cluster_A_orig.json"
cp output/vol-110/basins/bseed9_score460.json "$CORPUS_DIR/cluster_A_bseed9_score460.json"
cp output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json "$CORPUS_DIR/cluster_B_vol60_RECORD_459.json"
cp output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json "$CORPUS_DIR/canonical_457_seed4.json"
cp output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json "$CORPUS_DIR/canonical_457_seed10.json"
cp output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json "$CORPUS_DIR/canonical_457_seed7.json"
cp output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json "$CORPUS_DIR/canonical_458_vol32.json"

# Sweep (dedup)
python3 scripts/vol119_dedup_basin_corpus.py output/vol-119/corpus_v2_20260516T193029 --hamming-K 30 2>/dev/null | grep -E "\.json$" | while read p; do
    base=$(basename "$p")
    cp "$p" "$CORPUS_DIR/sweep_${base}"
done

# Plus the new 458 specifically
# (already included via dedup)

# Verify all
./target/release/verify_board "$CORPUS_DIR"/*.json 2>&1 | grep -E "(\.json|status)" | head -50

echo ""
echo "Corpus dir: $CORPUS_DIR"
echo "Total files: $(ls "$CORPUS_DIR"/*.json | wc -l)"
