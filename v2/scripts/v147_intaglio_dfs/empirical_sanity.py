#!/usr/bin/env python3
"""V147 — empirical sanity check on INTAGLIO post-placement check.

Claim under test: in edge-strict partials/finals, no COMPLETE 2x2 patch
should be forbidden under is_forbidden_2x2 (which asks: does ANY rotation
assignment make the 4 piece IDs fit? — but we already have a fixed
rotation that fits the surrounding pieces by edge-match).

Wait — is_forbidden_2x2 returns True if NO rotation makes the 2x2
internally consistent. If the board has the pieces with FIXED rotations
that DON'T match (because the board is ALNS-final with allowed
mismatches), then there might be SOME other rotation that would, OR
the piece-tuple might be intrinsically forbidden.

Two questions:
Q1. For complete 2x2 patches in real DB boards (mix of ALNS-final and
    DFS-partial origins), how many are forbidden?
Q2. For each forbidden patch, does the ACTUAL rotation in the board
    have all 4 internal edges matching?

Q2-yes + Q1-positive: edge-match doesn't imply piece-tuple feasibility.
That's the interesting case — would mean V147 DFS-pruner is non-trivial.

Q2-yes + Q1-zero: edge-match implies feasibility. V147 is vacuous on
strict DFS but useful on mismatch-allowing partials (ALNS-init).

Q2-no for some patch: edge-mismatch in real board. That patch can be
pruned by V147 even in strict DFS (but vanilla_fast wouldn't have
placed it; so vacuous still).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_puzzle(csv_path):
    """Returns pieces: list of (n,e,s,w) tuples indexed by piece_id."""
    pieces = []
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) < 4:
                continue
            try:
                # n,e,s,w
                n, e, s, w = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                pieces.append((n, e, s, w))
            except ValueError:
                continue
    return pieces


def rotate(piece, r):
    """Rotate piece (n,e,s,w) by r * 90° clockwise (matching Rust convention)."""
    # Rust: rotated[i] = base[(i + 4 - r) % 4]
    n, e, s, w = piece
    arr = [n, e, s, w]
    rotated = [arr[(i + 4 - r) % 4] for i in range(4)]
    return tuple(rotated)


def is_forbidden_2x2(pieces, p_tl, p_tr, p_bl, p_br):
    """Mirror of intaglio.rs is_forbidden_2x2.
    Returns True if no rotation assignment makes all 4 internal edges match."""
    BORDER = 0
    tl_p, tr_p, bl_p, br_p = pieces[p_tl], pieces[p_tr], pieces[p_bl], pieces[p_br]
    for r_tl in range(4):
        tl = rotate(tl_p, r_tl)  # (n,e,s,w)
        if tl[1] == BORDER or tl[2] == BORDER:
            continue
        for r_tr in range(4):
            tr = rotate(tr_p, r_tr)
            if tl[1] != tr[3]:
                continue
            if tr[2] == BORDER:
                continue
            for r_bl in range(4):
                bl = rotate(bl_p, r_bl)
                if tl[2] != bl[0]:
                    continue
                if bl[1] == BORDER:
                    continue
                for r_br in range(4):
                    br = rotate(br_p, r_br)
                    if tr[2] != br[0]:
                        continue
                    if bl[1] != br[3]:
                        continue
                    return False
    return True


def edges_match_2x2(pieces, placement_2x2):
    """Given 4 (piece_id, rotation) placements for TL, TR, BL, BR, return
    (n_internal_matches, all_match)."""
    BORDER = 0
    tl_pid, tl_rot = placement_2x2[0]
    tr_pid, tr_rot = placement_2x2[1]
    bl_pid, bl_rot = placement_2x2[2]
    br_pid, br_rot = placement_2x2[3]
    tl = rotate(pieces[tl_pid], tl_rot)
    tr = rotate(pieces[tr_pid], tr_rot)
    bl = rotate(pieces[bl_pid], bl_rot)
    br = rotate(pieces[br_pid], br_rot)
    matches = 0
    # 4 internal edges: TL.E-TR.W, TL.S-BL.N, TR.S-BR.N, BL.E-BR.W
    if tl[1] == tr[3] and tl[1] != BORDER:
        matches += 1
    if tl[2] == bl[0] and tl[2] != BORDER:
        matches += 1
    if tr[2] == br[0] and tr[2] != BORDER:
        matches += 1
    if bl[1] == br[3] and bl[1] != BORDER:
        matches += 1
    return matches


def load_board_json(path, size=16):
    """Load board JSON to placement[256] = (piece_id, rotation) or None."""
    with open(path) as f:
        d = json.load(f)
    pl = d.get("placement", [])
    out = [None] * (size * size)
    # Detect format: sparse (entries have explicit 'pos') vs indexed (position = list index).
    has_pos = any(isinstance(e, dict) and "pos" in e for e in pl)
    if has_pos:
        for entry in pl:
            if entry is None:
                continue
            pos = entry["pos"]
            out[pos] = (entry["piece_id"], entry["rotation"])
    else:
        for i, entry in enumerate(pl):
            if entry is None:
                continue
            if isinstance(entry, dict):
                out[i] = (entry["piece_id"], entry["rotation"])
    return out


def main():
    puzzle_csv = REPO.parent / "data" / "puzzles" / "size_16_official_eternity_joshua.csv"
    if not puzzle_csv.exists():
        puzzle_csv = REPO.parent / "data" / "benchmark" / "size_16_official_eternity.csv"
    print(f"[load] puzzle: {puzzle_csv}", flush=True)
    pieces = load_puzzle(puzzle_csv)
    print(f"[load] {len(pieces)} pieces", flush=True)
    if len(pieces) != 256:
        print(f"[ERROR] expected 256 pieces, got {len(pieces)}", file=sys.stderr)
        sys.exit(1)

    db_dir = REPO / "database-400-480"
    # Sample boards stratified by score: low/mid/high to see how forbidden-count varies.
    all_boards = sorted(db_dir.glob("*.json"))
    # Score prefix in filename (e.g., "459_..." or "400_..."). Stratify.
    by_score = {}
    for bp in all_boards:
        prefix = bp.name.split("_", 1)[0]
        try:
            score = int(prefix)
        except ValueError:
            continue
        by_score.setdefault(score, []).append(bp)
    scores = sorted(by_score.keys())
    print(f"[scan] {len(all_boards)} total; score range {scores[0]}-{scores[-1]}", flush=True)
    # Pick 5 from each of: low (400-440), mid (440-459), high (459-470).
    low = [b for s in scores if 400 <= s <= 440 for b in by_score[s]][:8]
    mid = [b for s in scores if 441 <= s <= 458 for b in by_score[s]][:8]
    high = [b for s in scores if 459 <= s <= 470 for b in by_score[s]][:8]
    boards = low + mid + high
    print(f"[scan] sampling {len(low)} low + {len(mid)} mid + {len(high)} high = {len(boards)} boards",
          flush=True)

    N = 16
    total_complete_2x2 = 0
    total_forbidden_2x2 = 0
    total_edge_mismatch_in_forbidden = 0
    total_edge_mismatch_in_feasible = 0

    for bp in boards:
        placement = load_board_json(bp, size=N)
        bname = bp.name[:60]
        n_complete = 0
        n_forbidden = 0
        n_mismatch_forbidden = 0
        n_mismatch_feasible = 0
        for y in range(N - 1):
            for x in range(N - 1):
                idx_tl = y * N + x
                idx_tr = y * N + (x + 1)
                idx_bl = (y + 1) * N + x
                idx_br = (y + 1) * N + (x + 1)
                if any(placement[i] is None for i in (idx_tl, idx_tr, idx_bl, idx_br)):
                    continue
                n_complete += 1
                p_tl = placement[idx_tl][0]
                p_tr = placement[idx_tr][0]
                p_bl = placement[idx_bl][0]
                p_br = placement[idx_br][0]
                forbidden = is_forbidden_2x2(pieces, p_tl, p_tr, p_bl, p_br)
                edge_matches = edges_match_2x2(
                    pieces,
                    (placement[idx_tl], placement[idx_tr], placement[idx_bl], placement[idx_br])
                )
                full_match = (edge_matches == 4)
                if forbidden:
                    n_forbidden += 1
                    if full_match:
                        n_mismatch_forbidden += 1  # this would be SURPRISING
                else:
                    if not full_match:
                        n_mismatch_feasible += 1
        total_complete_2x2 += n_complete
        total_forbidden_2x2 += n_forbidden
        total_edge_mismatch_in_forbidden += n_mismatch_forbidden
        total_edge_mismatch_in_feasible += n_mismatch_feasible
        print(f"  {bname}: complete={n_complete} forbidden={n_forbidden} "
              f"forbidden+full_match={n_mismatch_forbidden} "
              f"feasible+partial_match={n_mismatch_feasible}",
              flush=True)

    print()
    print(f"[summary] {len(boards)} boards, total {total_complete_2x2} complete 2x2 patches")
    print(f"  forbidden patches: {total_forbidden_2x2} ({total_forbidden_2x2/max(1,total_complete_2x2)*100:.2f}%)")
    print(f"  forbidden + full-edge-match: {total_edge_mismatch_in_forbidden} ({total_edge_mismatch_in_forbidden/max(1,total_complete_2x2)*100:.4f}%)")
    print(f"  feasible + partial-edge-match: {total_edge_mismatch_in_feasible} ({total_edge_mismatch_in_feasible/max(1,total_complete_2x2)*100:.2f}%)")
    print()
    print("INTERPRETATION:")
    print("  - forbidden+full_match = 0 → V147 vacuous on edge-strict DFS")
    print("  - forbidden+full_match > 0 → V147 has prune power BEYOND edge matching")


if __name__ == "__main__":
    main()
