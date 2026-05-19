#!/usr/bin/env python3
"""V129-T7 — Escape-pinning v2: TOP-K only.

V129-T6 pinned ALL 251 escape positions → board reassembles into
McGavin basin at 451/480. ALNS with 251 pins has no freedom, so it'll
just polish to ~466-469 (close to McGavin).

This version pins only the TOP-K escape positions (those with highest
trap counts in the source 461 basin). ALNS then has 256-K freedom to
explore. We test K ∈ {16, 32, 64} to find the sweet spot.

Hypothesis: with K=32, the pinned escape pieces are PERTURBATION enough
to leave our 461 basin but not enough to force McGavin; ALNS should
find a NOVEL basin > 461.
"""

from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HINTS = {34, 45, 135, 210, 221}


def load_record(p):
    d = json.load(open(p))
    pl = {}
    for i, pp in enumerate(d.get("placement", [])):
        if isinstance(pp, dict):
            pl[int(pp.get("pos", i))] = (int(pp["piece_id"]), int(pp["rotation"]))
    return pl, d


def main():
    res = json.load(open(REPO / "output/vol-129/trap_pieces_per_position/result.json"))

    # Rank positions by TOP-TRAP COUNT (the most strongly trapped positions
    # are most worth pinning to the escape piece).
    pos_trap_strength = []
    for pos_str, traps in res["trap_pieces"].items():
        pos = int(pos_str)
        if pos in HINTS: continue
        escapes = res["escape_pieces"].get(pos_str, [])
        if not traps or not escapes: continue
        top_trap_count = traps[0][2]
        pos_trap_strength.append((pos, top_trap_count, traps[0], escapes[0]))
    pos_trap_strength.sort(key=lambda x: -x[1])

    BASE = REPO / "output/vol-125/records/RECORD_461_bf_bw_off110_seed42.json"
    base_pl, _ = load_record(BASE)

    OUT_DIR = REPO / "output/vol-129" / f"escape_v2_{time.strftime('%Y%m%dT%H%M%S')}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"OUT_DIR={OUT_DIR}", flush=True)

    SEEDS = [42, 1]
    procs = []

    for K in [16, 32, 64]:
        # Pick top-K trap positions; apply escape piece overlay.
        chosen = pos_trap_strength[:K]
        overlay = {pos: (esc[0], esc[1]) for pos, _, _, esc in chosen}

        # Apply via incremental swap.
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

        # Save.
        start_path = OUT_DIR / f"start_K{K}.json"
        with open(start_path, "w") as f:
            json.dump({"matched": -1,
                       "placement": [{"pos": p, "piece_id": pr[0], "rotation": pr[1]}
                                     for p, pr in sorted(new_pl.items())],
                       "K": K, "applied": applied}, f, indent=2)
        r = subprocess.run([str(REPO / "target/bench-fast/rescore_board"), str(start_path)],
                          capture_output=True, text=True)
        score_line = r.stdout.strip().split("\n")[-1]
        print(f"K={K} applied={applied}  rescored: {score_line}", flush=True)

        # Pin overlay positions.
        extra_hints = []
        for pos in sorted(overlay.keys()):
            extra_hints.extend(["--extra-hint", str(pos)])

        for seed in SEEDS:
            log = OUT_DIR / f"alns_K{K}_s{seed}.log"
            cmd = [str(REPO / "target/bench-fast/alns_only"),
                   "--cp-board", str(start_path),
                   "--ops", "basic",
                   "--alns-budget-ms", "1800000",
                   "--seed", str(seed)] + extra_hints
            f = open(log, "w")
            p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
            procs.append((K, seed, p, f, log))

    print(f"\nLaunched {len(procs)} ALNS jobs (6 = 2 seeds × 3 K values).", flush=True)
    for K, seed, p, f, log in procs:
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
        print(f"  K={K} seed={seed}: best={best}", flush=True)

    summary = {}
    for K, seed, p, f, log in procs:
        with open(log) as fh:
            content = fh.read()
        scores = []
        for line in content.split("\n"):
            if "matched=" in line:
                try: scores.append(int(line.split("matched=")[1].split()[0].strip(",")))
                except: pass
        summary[f"K{K}_s{seed}"] = max(scores) if scores else None
    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
