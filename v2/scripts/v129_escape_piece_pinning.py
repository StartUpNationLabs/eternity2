#!/usr/bin/env python3
"""V129-T6 — PALIMPSEST escape-piece pinning.

From v129_trap_pieces_per_position, get the ESCAPE pieces at trap-heavy
border positions. Build a starting board where those escape pieces are
pinned at their target positions (override 461 base), then run ALNS basic.

The hypothesis: the 461 basin family is locked by SPECIFIC TRAP PIECES
at border positions. Replacing them with the ESCAPE pieces (taken from
462+ boards) and letting ALNS fill should explore basins that lead to
462+.

Critical detail: ESCAPE pieces come from McGavin's 469 basin (the
462-469 boards in our DB). Pinning these forces our search toward
McGavin. We're testing if that's reachable from a partial McGavin-pinned
start, NOT requiring the full McGavin pin set.
"""

from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path
from collections import defaultdict
import random

REPO = Path(__file__).resolve().parents[1]
W = 16
N_CELLS = 256
HINTS = {34, 45, 135, 210, 221}


def load_record(p):
    d = json.load(open(p))
    pl = {}
    for i, pp in enumerate(d.get("placement", [])):
        if isinstance(pp, dict):
            pl[int(pp.get("pos", i))] = (int(pp["piece_id"]), int(pp["rotation"]))
    return pl, d


def main():
    # Load trap/escape result.
    res_path = REPO / "output/vol-129/trap_pieces_per_position/result.json"
    res = json.load(open(res_path))
    print(f"Source: {res_path}", flush=True)

    # Build escape overlay: at each position with a TRAP piece, place the
    # top ESCAPE piece (if any).
    overlay = {}
    for pos_str, traps_list in res["trap_pieces"].items():
        pos = int(pos_str)
        if pos in HINTS: continue
        traps = traps_list
        escapes = res["escape_pieces"].get(pos_str, [])
        if not traps or not escapes: continue
        # Pick the top escape (most popular in 462+ boards).
        pid, rot, cnt = escapes[0]
        overlay[pos] = (pid, rot)
    print(f"Overlay positions: {len(overlay)}", flush=True)

    # Base 461.
    BASE = REPO / "output/vol-125/records/RECORD_461_bf_bw_off110_seed42.json"
    base_pl, _ = load_record(BASE)

    # Apply overlay via incremental swap (same idea as cross-basin probe).
    new_pl = dict(base_pl)
    cur_pos_of_pid = {pid: pos for pos, (pid, _) in new_pl.items()}
    applied = 0
    for pos_target, (pid_target, rot_target) in overlay.items():
        pos_source = cur_pos_of_pid.get(pid_target)
        if pos_source is None: continue
        if pos_source == pos_target:
            new_pl[pos_target] = (pid_target, rot_target)
            applied += 1
            continue
        bumped = new_pl[pos_target]
        new_pl[pos_target] = (pid_target, rot_target)
        new_pl[pos_source] = bumped
        cur_pos_of_pid[pid_target] = pos_target
        cur_pos_of_pid[bumped[0]] = pos_source
        applied += 1

    # Verify uniqueness.
    pids = [pid for pid, _ in new_pl.values()]
    assert len(set(pids)) == 256, "duplicate pieces"
    print(f"Overlay applied to {applied} positions, board valid (256 distinct pieces).", flush=True)

    OUT_DIR = REPO / "output/vol-129" / f"escape_pinning_{time.strftime('%Y%m%dT%H%M%S')}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"OUT_DIR={OUT_DIR}", flush=True)

    start_path = OUT_DIR / "starting_board.json"
    with open(start_path, "w") as f:
        json.dump({"matched": -1,
                   "placement": [{"pos": p, "piece_id": pr[0], "rotation": pr[1]}
                                 for p, pr in sorted(new_pl.items())]}, f, indent=2)
    r = subprocess.run([str(REPO / "target/bench-fast/rescore_board"), str(start_path)],
                      capture_output=True, text=True)
    print(f"Rescore: {r.stdout.strip().split(chr(10))[-1]}", flush=True)

    # Pin overlay positions in ALNS.
    extra_hints = []
    for pos in sorted(overlay.keys()):
        extra_hints.extend(["--extra-hint", str(pos)])
    print(f"Pinning {len(overlay)} extra positions in ALNS", flush=True)

    SEEDS = [42, 1, 7, 99, 142, 5257]
    procs = []
    for seed in SEEDS:
        log = OUT_DIR / f"alns_seed{seed}.log"
        cmd = [str(REPO / "target/bench-fast/alns_only"),
               "--cp-board", str(start_path),
               "--ops", "basic",
               "--alns-budget-ms", "1800000",
               "--seed", str(seed)] + extra_hints
        f = open(log, "w")
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
        procs.append((seed, p, f, log))
        print(f"  launched seed={seed} pid={p.pid}", flush=True)

    print(f"\nWaiting for {len(procs)} ALNS jobs (30min)...", flush=True)
    for seed, p, f, log in procs:
        p.wait()
        f.close()
        with open(log) as fh:
            content = fh.read()
        scores = []
        for line in content.split("\n"):
            if "matched=" in line:
                try: scores.append(int(line.split("matched=")[1].split()[0].strip(",")))
                except: pass
        best = max(scores) if scores else None
        print(f"  seed={seed}: best={best}", flush=True)


if __name__ == "__main__":
    main()
