#!/usr/bin/env python3
"""V125-T34c — FPL cross-basin probe.

Use the McGavin-only pair signature (output of v125_fpl_basin_split.py)
to pin McGavin-bottom pieces onto our 461 basin starting board, then
ALNS basic 30min × multiple seeds.

Three possible outcomes:
1. ALNS converges to 469 → we've successfully transported into McGavin's
   basin (interesting but not novel — McGavin already known).
2. ALNS converges to a HYBRID score > 461 in some new corner-perm →
   genuine new basin discovered (THE WIN).
3. ALNS regresses (≤ 461) → basin transport infeasible: McGavin-bottom
   incompatible with our 461 top. (Useful refutation.)

Implementation: take RECORD_461_off110_seed1.json, REPLACE pieces at
McGavin-bottom positions with McGavin-canonical pieces (per fpl output),
save as a new partial JSON, then run alns_only --cp-board on it.

Note: this puts the board in an INVALID state initially (some pieces
used twice). ALNS basic preset should detect and repair — its
`worst_band` operator will destroy the most-conflicting region first.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
W = 16
N_CELLS = 256

# Source: our 461 basin
BASE_BOARD = REPO / "output/vol-125/records/RECORD_461_bf_bw_off110_seed42.json"
if not BASE_BOARD.exists():
    # Fallback to off110 seed1
    for f in REPO.glob("**/RECORD_461*.json"):
        BASE_BOARD = f
        break

# FPL output dir (latest)
FPL_DIRS = sorted((REPO / "output/vol-125").glob("fpl_basin_*"), key=lambda p: p.stat().st_mtime)
assert FPL_DIRS, "no fpl_basin output found — run v125_fpl_basin_split.py first"
FPL_DIR = FPL_DIRS[-1]
FPL_JSON = FPL_DIR / "fpl_mcgavin_pairs.json"
print(f"FPL_DIR={FPL_DIR}", flush=True)
print(f"BASE_BOARD={BASE_BOARD}", flush=True)

# Output
OUT_DIR = REPO / "output/vol-125" / f"fpl_cross_basin_{time.strftime('%Y%m%dT%H%M%S')}"
OUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"OUT_DIR={OUT_DIR}", flush=True)


def load_placement(path: Path):
    d = json.load(open(path))
    pl = {}
    for i, p in enumerate(d.get("placement", [])):
        if isinstance(p, dict):
            pos = p.get("pos", i)
            pl[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    return pl, d


def main():
    fpl = json.load(open(FPL_JSON))
    base_pl, base_d = load_placement(BASE_BOARD)
    print(f"Base: matched={base_d.get('matched')} placed={len(base_pl)}", flush=True)

    # Take top-K McGavin-only pairs. Build target placement at McGavin-bottom positions.
    # Each pair-tuple gives us: at position i and j, pieces (pi,ri) and (pj,rj).
    # We aggregate per-position: position i wants piece (pi,ri).
    # When the same position appears in multiple pairs with different (pi,ri), take majority.
    K = 50
    top_pairs = fpl["top_pairs"][:K]

    desired: dict[int, dict[tuple[int, int], int]] = {}  # pos → {(pid, rot): count}
    for pair in top_pairs:
        for pos_key, pid_key, rot_key in [("i", "pi", "ri"), ("j", "pj", "rj")]:
            pos = pair[pos_key]
            pid = pair[pid_key]
            rot = pair[rot_key]
            d = desired.setdefault(pos, {})
            d[(pid, rot)] = d.get((pid, rot), 0) + 1

    # Resolve majority per position.
    pinned_overlay: dict[int, tuple[int, int]] = {}
    for pos, votes in desired.items():
        (pid, rot), _ = max(votes.items(), key=lambda x: x[1])
        pinned_overlay[pos] = (pid, rot)
    print(f"Pinned-overlay covers {len(pinned_overlay)} positions", flush=True)
    print(f"Position range: {min(pinned_overlay)} - {max(pinned_overlay)}", flush=True)

    # Build the new starting board: take base, but at pinned_overlay positions,
    # FORCE McGavin pieces. To keep board valid (each piece once), we need to:
    # 1. Place McGavin pieces at pinned positions.
    # 2. Wherever a McGavin piece was elsewhere in base, REMOVE it (now duplicate).
    # 3. Wherever base piece is bumped, place it where the McGavin piece WAS.
    # This is a piece-swap by piece-id: positionA<->positionB where positionA
    # holds (mcgavin_pid in base) and positionB is pinned target.

    # Process overlay incrementally: at each step, find the piece in
    # CURRENT board (not original), swap into target, update both maps.
    # Then verify post-swap uniqueness. If a pair conflicts (target piece
    # already moved by an earlier pair to a different spot), skip it.
    new_pl = dict(base_pl)
    cur_pos_of_pid: dict[int, int] = {pid: pos for pos, (pid, _) in new_pl.items()}
    swap_log = []
    skipped = 0
    for pos_target, (pid_target, rot_target) in pinned_overlay.items():
        pos_source = cur_pos_of_pid.get(pid_target)
        if pos_source is None:
            skipped += 1
            continue
        if pos_source == pos_target:
            new_pl[pos_target] = (pid_target, rot_target)
            continue
        bumped_pid, bumped_rot = new_pl[pos_target]
        # Apply swap.
        new_pl[pos_target] = (pid_target, rot_target)
        new_pl[pos_source] = (bumped_pid, bumped_rot)
        cur_pos_of_pid[pid_target] = pos_target
        cur_pos_of_pid[bumped_pid] = pos_source
        swap_log.append((pos_source, pos_target, pid_target, bumped_pid))

    print(f"Swaps: {len(swap_log)}", flush=True)

    # Verify uniqueness.
    pids = [pid for pid, _ in new_pl.values()]
    if len(set(pids)) != len(pids):
        from collections import Counter
        c = Counter(pids)
        dups = [(p, n) for p, n in c.items() if n > 1]
        print(f"ERROR: duplicate pids: {dups[:10]}", flush=True)
        sys.exit(1)
    print(f"Uniqueness OK: {len(set(pids))} distinct pieces", flush=True)

    # Save new starting board.
    starting_path = OUT_DIR / "starting_board_with_mcgavin_overlay.json"
    new_placement_list = [
        {"pos": pos, "piece_id": pid, "rotation": rot}
        for pos, (pid, rot) in sorted(new_pl.items())
    ]
    with open(starting_path, "w") as f:
        json.dump({
            "matched": -1,
            "placement": new_placement_list,
            "source": str(BASE_BOARD.name),
            "overlay_positions": sorted(pinned_overlay.keys()),
            "n_swaps": len(swap_log),
        }, f, indent=2)
    print(f"Wrote starting board: {starting_path}", flush=True)

    # Rescore.
    rescore_cmd = [str(REPO / "target/bench-fast/rescore_board"), str(starting_path)]
    r = subprocess.run(rescore_cmd, capture_output=True, text=True)
    print(f"Rescore: {r.stdout.strip()}", flush=True)
    if r.stderr:
        print(f"Stderr: {r.stderr.strip()}", flush=True)

    # Build extra-hint arguments for ALNS: pin all overlay positions.
    extra_hints = []
    for pos in sorted(pinned_overlay.keys()):
        extra_hints.extend(["--extra-hint", str(pos)])
    print(f"Pinning {len(pinned_overlay)} extra positions in ALNS", flush=True)

    # Launch ALNS basic 30min × 6 seeds (1 core free, only 6 in parallel).
    SEEDS = [42, 1, 7, 99, 142, 5257]
    procs = []
    for seed in SEEDS:
        log = OUT_DIR / f"alns_seed{seed}.log"
        cmd = [
            str(REPO / "target/bench-fast/alns_only"),
            "--cp-board", str(starting_path),
            "--ops", "basic",
            "--alns-budget-ms", "1800000",
            "--seed", str(seed),
        ] + extra_hints
        f = open(log, "w")
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
        procs.append((seed, p, f, log))
        print(f"  launched seed={seed} pid={p.pid} → {log.name}", flush=True)

    # Wait.
    print(f"\nWaiting for 6 ALNS jobs (30min each) ...", flush=True)
    for seed, p, f, log in procs:
        p.wait()
        f.close()
        # Quick result.
        with open(log) as fh:
            content = fh.read()
        scores = []
        for line in content.split("\n"):
            if "matched=" in line:
                tok = line.split("matched=")[1].split()[0].strip(",")
                try:
                    scores.append(int(tok))
                except: pass
        best = max(scores) if scores else None
        print(f"  seed={seed}: best matched={best}", flush=True)


if __name__ == "__main__":
    main()
