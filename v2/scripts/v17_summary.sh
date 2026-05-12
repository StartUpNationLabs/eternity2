#!/bin/bash
# Summarize all v17 run results from output/v17_runs/.
# Run anytime to see the current scoreboard.
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
printf "=== v17 results scoreboard ===\n"
printf "%-40s  %s\n" "RUN" "RESULT"
for log in output/v17_runs/*.stderr.log; do
    name=$(basename "$log" .stderr.log)
    # Extract ALNS final line
    line=$(grep "ALNS:" "$log" 2>/dev/null | tail -1)
    if [[ -n "$line" ]]; then
        matched=$(echo "$line" | grep -oE "matched=[0-9]+/480" | head -1)
        printf "%-40s  %s\n" "$name" "$matched"
    else
        # Maybe still in CP
        line=$(grep "CP:" "$log" 2>/dev/null | tail -1)
        if [[ -n "$line" ]]; then
            printf "%-40s  CP=%s\n" "$name" "$(echo "$line" | grep -oE "matched=[0-9]+/480" | head -1)"
        else
            printf "%-40s  (no result yet)\n" "$name"
        fi
    fi
done
echo
echo "Best so far:"
grep "ALNS:" output/v17_runs/*.stderr.log 2>/dev/null | grep -oE "matched=[0-9]+/480" | sort -t= -k2 -nr | head -3
