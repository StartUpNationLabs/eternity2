#!/usr/bin/env bash
# V182 ENGRAVE — try CSP-fill on each row-band of a 460 board.
# For each (row_start, row_height) ∈ valid configs, strip + CSP-fill.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

INPUT="${1:-output/vol-155/RECORD_460_alns_from_456_seed1_lkh.json}"
OUT=output/vol-182/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT"
echo "[v182] input=$INPUT out=$OUT" | tee "$OUT/_meta.log"

n=0
BATCH=8
for hgt in 1 2 3; do
  for row_start in $(seq 0 $((16 - hgt))); do
    row_end=$((row_start + hgt))
    # Skip if band contains pinned hint positions.
    # Hint positions: 135, 210, 34, 221, 45 → rows 8, 13, 2, 13, 2.
    # Filter: skip bands intersecting rows {2, 8, 13}.
    skip=0
    for r in 2 8 13; do
      if [ "$r" -ge "$row_start" ] && [ "$r" -lt "$row_end" ]; then
        skip=1
        break
      fi
    done
    if [ "$skip" = "1" ]; then continue; fi
    tag="h${hgt}_r${row_start}"
    part="$OUT/${tag}_part.json"
    out_json="$OUT/${tag}_filled.json"
    log="$OUT/${tag}.log"
    uv run python scripts/v182_engrave/strip_band.py \
      --input "$INPUT" \
      --out "$part" \
      --row-start "$row_start" --row-end "$row_end" \
      > /dev/null 2>&1
    nice -n 19 target/bench-fast/border_to_csp_fill \
      --board "$part" \
      --budget-ms 30000 \
      --solver gacolor_ac3_par \
      --seed 1 \
      --out "$out_json" \
      --max-score \
      > "$log" 2>&1 &
    n=$((n + 1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v182] $n bands done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "" | tee -a "$OUT/_meta.log"
echo "[v182] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT"/h*.log; do
  tag=$(basename "$log" .log)
  m=$(grep -oE 'matched: [0-9]+ -> [0-9]+' "$log" | tail -1 | grep -oE '[0-9]+$')
  placed=$(grep -oE 'placed: [0-9]+ -> [0-9]+' "$log" | tail -1 | grep -oE '[0-9]+$')
  echo "  $tag: matched=$m placed=$placed/256" | tee -a "$OUT/_meta.log"
done

# Top 5.
echo "" | tee -a "$OUT/_meta.log"
echo "[v182] Top 5:" | tee -a "$OUT/_meta.log"
for log in "$OUT"/h*.log; do
  tag=$(basename "$log" .log)
  m=$(grep -oE 'matched: [0-9]+ -> [0-9]+' "$log" | tail -1 | grep -oE '[0-9]+$')
  if [ -n "$m" ]; then echo "$m $tag"; fi
done | sort -rn | head -5 | tee -a "$OUT/_meta.log"
echo "[v182] done $(date)" | tee -a "$OUT/_meta.log"
