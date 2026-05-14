#!/usr/bin/env bash
# Vol-34 — verify every T3 ALNS run by rescore_board on its saved board.
# Updates summary.jsonl with a "rescore" field and flags mismatches.

set -euo pipefail
cd "$(dirname "$0")/.."

SUMMARY="${1:-output/vol-34/t3_full/summary.jsonl}"
LOG_DIR="${2:-output/vol-34/t3_full/logs}"
OUT="${SUMMARY}.verified.jsonl"
: > "$OUT"

cat "$SUMMARY" | while read -r line; do
    partial=$(echo "$line" | jq -r '.partial')
    seed=$(echo "$line" | jq -r '.seed')
    logged=$(echo "$line" | jq -r '.matched')
    # Find the corresponding log
    stem=$(basename "$partial" .json)
    log="$LOG_DIR/${stem}_seed${seed}.log"
    if [ ! -f "$log" ]; then
        echo "$line" | jq -c '. + {rescore: null, note: "log missing"}' >> "$OUT"
        continue
    fi
    saved=$(grep -h saved: "$log" | awk '{print $2}' | tail -1)
    if [ -z "$saved" ] || [ ! -f "$saved" ]; then
        echo "$line" | jq -c '. + {rescore: null, note: "saved missing"}' >> "$OUT"
        continue
    fi
    rescore=$(./target/release/rescore_board "$saved" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    if [ "$logged" = "$rescore" ]; then
        echo "$line" | jq -c ". + {rescore: $rescore, ok: true}" >> "$OUT"
    else
        echo "DISCREPANCY $stem seed=$seed: logged=$logged rescore=$rescore"
        echo "$line" | jq -c ". + {rescore: $rescore, ok: false, saved: \"$saved\"}" >> "$OUT"
    fi
done

echo ""
echo "=== verified summary ==="
echo "total runs: $(wc -l < "$OUT")"
echo "consistent (ok=true): $(jq -s 'map(select(.ok == true)) | length' "$OUT")"
echo "discrepant (ok=false): $(jq -s 'map(select(.ok == false)) | length' "$OUT")"
echo ""
echo "=== top by true score ==="
jq -s 'sort_by(-.rescore // 0)[:10]' "$OUT" | jq -r '.[] | "  \(.rescore // "??")  \(.partial | sub(".*/";"")) seed=\(.seed) (logged=\(.matched))"'
