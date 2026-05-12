#!/bin/bash
# Summarize all v17 run results across multiple directories.
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
echo "=== v17 results scoreboard ==="
echo

show_logs() {
    local pattern=$1
    local dir=$2
    [[ ! -d "$dir" ]] && return
    for log in $(ls -t $dir/$pattern 2>/dev/null); do
        name=$(basename "$log" .stderr.log)
        line=$(grep -E "ALNS:|matched=[0-9]+/480 placed" "$log" 2>/dev/null | tail -1)
        if [[ -n "$line" ]]; then
            matched=$(echo "$line" | grep -oE "matched=[0-9]+/480" | head -1)
            printf "  %-45s  %s\n" "$name" "$matched"
        else
            cp_line=$(grep "CP:" "$log" 2>/dev/null | tail -1)
            if [[ -n "$cp_line" ]]; then
                m=$(echo "$cp_line" | grep -oE "matched=[0-9]+/480" | head -1)
                printf "  %-45s  CP=%s\n" "$name" "$m"
            else
                printf "  %-45s  (pending)\n" "$name"
            fi
        fi
    done
}

echo "[v17 main runs in output/v17_runs/]"
show_logs "*.stderr.log" "output/v17_runs"
echo
echo "[v17 experiment runs in output/v17_exp/]"
show_logs "E*.stderr.log" "output/v17_exp"
echo
echo "[alns_only saved boards in output/v17_alns_only/]"
for json in $(ls -t output/v17_alns_only/*.json 2>/dev/null); do
    matched=$(python3 -c "import json; d=json.load(open('$json')); print(d.get('matched', d.get('matched_best', '?')))" 2>/dev/null)
    printf "  %-45s  matched=%s\n" "$(basename $json .json)" "$matched"
done | head -10
echo
echo "[alns_portfolio in output/v17_alns_portfolio/]"
for json in $(ls -t output/v17_alns_portfolio/*.json 2>/dev/null); do
    matched=$(python3 -c "import json; d=json.load(open('$json')); print(d.get('matched_best', '?'))" 2>/dev/null)
    printf "  %-45s  matched=%s\n" "$(basename $json .json)" "$matched"
done | head -10
echo
echo "[alns_pt in output/v17_alns_pt/]"
for json in $(ls -t output/v17_alns_pt/*.json 2>/dev/null); do
    matched=$(python3 -c "import json; d=json.load(open('$json')); print(d.get('matched_best', '?'))" 2>/dev/null)
    printf "  %-45s  matched=%s\n" "$(basename $json .json)" "$matched"
done | head -10
echo
echo "[cluster_repair in output/v17_cluster_repair/]"
for json in $(ls -t output/v17_cluster_repair/board_*.json 2>/dev/null); do
    matched=$(python3 -c "import json; d=json.load(open('$json')); print(d.get('matched_out', '?'))" 2>/dev/null)
    printf "  %-45s  matched=%s\n" "$(basename $json .json)" "$matched"
done | head -10
echo
echo "[alns_cluster_loop in output/v17_alns_cluster/]"
for json in $(ls -t output/v17_alns_cluster/final_*.json 2>/dev/null); do
    matched=$(python3 -c "import json; d=json.load(open('$json')); print(d.get('matched_best', '?'))" 2>/dev/null)
    printf "  %-45s  matched=%s\n" "$(basename $json .json)" "$matched"
done | head -10
echo
echo "[v17_cold_portfolio]"
for log in $(ls -t output/v17_cold_portfolio/*/summary.json 2>/dev/null); do
    name=$(dirname $log | xargs basename)
    arm_best=$(python3 -c "import json; d=json.load(open('$log')); rs=d.get('results',[]); print(max((r['alns']['matched'] for r in rs), default='?'), 'over', len(rs), 'arms')" 2>/dev/null)
    printf "  %-45s  best=%s\n" "$name" "$arm_best"
done | head -5

echo
echo "=== Top matched scores across all v17 runs ==="
{
    grep -h "ALNS:" output/v17_*/*.stderr.log 2>/dev/null | grep -oE "matched=[0-9]+/480"
    grep -h "ALNS:" output/v17_*/*/*.stderr.log 2>/dev/null | grep -oE "matched=[0-9]+/480"
    grep -h "matched=[0-9]\+/480" output/v17_runs/*.stderr.log 2>/dev/null | grep -oE "matched=[0-9]+/480"
} | sort -t= -k2 -nr | uniq -c | head -10
