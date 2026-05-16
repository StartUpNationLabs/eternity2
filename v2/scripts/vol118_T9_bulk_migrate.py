#!/usr/bin/env python3
"""Vol-118 T9 — bulk-migrate per-bin load_board to canonical.

Replaces fn load_board functions with thin wrappers. Uses brace-matching
to find function bounds (not regex, which gets tangled with nested braces).
"""

import sys
from pathlib import Path

DRY = '--dry-run' in sys.argv

BIN_DIR = Path('/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2/crates/bench-audit/src/bin')

REPLACEMENT_RESULT = """// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}"""

REPLACEMENT_BOARD = """// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> eternity2_core::Board {
    eternity2_export::load_board(path, puzzle).expect("load_board")
}"""

REPLACEMENT_BOARD_NOPUZZLE = """// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path) -> eternity2_core::Board {
    let puzzle_path = std::path::PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = eternity2_benchmark::loader::load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eternity2_export::load_board(path, &puzzle).expect("load_board")
}"""

SKIP = {
    'verify_board.rs', 'print_bucas.rs', 'rescore_board.rs',
    'diff_boards.rs', 'edge_target_match.rs', 'edge_bound_ascent.rs',
}

def find_load_board_func(text):
    """Find a fn load_board function. Returns (start_idx, end_idx_exclusive, signature_line)
    or None if not found. Uses brace-matching."""
    sig_start = text.find('\nfn load_board')
    if sig_start < 0:
        sig_start = text.find('fn load_board')
        if sig_start < 0:
            return None
    else:
        sig_start += 1  # skip leading \n

    # Find the opening brace
    open_brace = text.find('{', sig_start)
    if open_brace < 0:
        return None

    # Match braces from open_brace
    depth = 1
    i = open_brace + 1
    while i < len(text) and depth > 0:
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    if depth != 0:
        return None

    # i now points just past the closing }
    end = i
    # Get signature line for inspection
    sig_end = text.find('\n', sig_start)
    signature = text[sig_start:sig_end] if sig_end > sig_start else text[sig_start:sig_start+100]
    return (sig_start, end, signature)

def classify_pattern(signature):
    """Return one of: 'result_with_puzzle', 'board_with_puzzle',
    'board_nopuzzle', None."""
    sig = signature.strip()
    if 'fn load_board' not in sig:
        return None
    if 'Result<Board' in sig and 'puzzle' in sig:
        return 'result_with_puzzle'
    if '-> Board' in sig and 'puzzle' in sig:
        return 'board_with_puzzle'
    if '-> Board' in sig and 'puzzle' not in sig:
        return 'board_nopuzzle'
    return None

def migrate(path):
    text = path.read_text()
    found = find_load_board_func(text)
    if found is None:
        return False
    start, end, sig = found
    kind = classify_pattern(sig)
    if kind is None:
        return False
    repl = {
        'result_with_puzzle': REPLACEMENT_RESULT,
        'board_with_puzzle': REPLACEMENT_BOARD,
        'board_nopuzzle': REPLACEMENT_BOARD_NOPUZZLE,
    }[kind]

    new_text = text[:start] + repl + text[end:]

    if DRY:
        print(f"WOULD MIGRATE ({kind}): {path.name}  ({sig.strip()})")
    else:
        path.write_text(new_text)
        print(f"MIGRATED ({kind}): {path.name}")
    return True

if __name__ == "__main__":
    total = 0
    migrated = 0
    for f in sorted(BIN_DIR.glob('*.rs')):
        if f.name in SKIP:
            continue
        total += 1
        if migrate(f):
            migrated += 1
    print(f"\nMigrated {migrated}/{total} bins")
