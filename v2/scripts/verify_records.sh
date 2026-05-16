#!/bin/bash
# Canonical record verification — run this on any board claimed as a record.
# Per CLAUDE.md rule #5: every record claim must pass these checks.
#
# Vol-118 T7: rewritten to use the consolidated `verify_board` bin which
# replaces both `rescore_board` and `verify_record` (those still exist but
# are now legacy; their checks are subsets of verify_board's).
#
# Usage: verify_records.sh <board.json> [board.json ...]
#
# verify_board checks:
#   - piece-uniqueness (no duplicate pieces placed)
#   - border-consistency (no edge pieces at interior, no interior pieces
#     with BORDER edges facing outward) -- catches vol-118 bf-bucket-bug class
#   - hint-compliance (canonical hints in pinned positions+rotations)
#   - edge-match score (matched/total adjacencies)

set -uo pipefail

cd "$(dirname "$0")/.."

if [ $# -eq 0 ]; then
    echo "usage: $0 <board.json> [board.json ...]"
    echo ""
    echo "Per CLAUDE.md rule #5: every record claim must pass these checks before being filed."
    exit 2
fi

./target/release/verify_board "$@"
