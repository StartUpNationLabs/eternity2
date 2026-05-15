#!/bin/bash
# Canonical record verification — run this on any board claimed as a record.
# Per CLAUDE.md rule #5: every record claim must pass these checks.
#
# Usage: verify_records.sh <board.json> [board.json ...]
#
# Runs:
#   1. rescore_board — independent score recomputation
#   2. verify_record — piece-uniqueness + hint compliance

set -uo pipefail

cd "$(dirname "$0")/.."

if [ $# -eq 0 ]; then
    echo "usage: $0 <board.json> [board.json ...]"
    echo ""
    echo "Per CLAUDE.md rule #5: every record claim must pass these checks before being filed."
    exit 2
fi

echo "=== rescore_board (independent score) ==="
./target/release/rescore_board "$@"
echo ""
echo "=== verify_record (piece-uniqueness + hint compliance) ==="
./target/release/verify_record "$@"
