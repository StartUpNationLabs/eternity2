#!/usr/bin/env python3
"""Summarize a NE2 K-sweep across multiple per-K pt_e2 JSONs.

Usage:
    python3 scripts/ne2_analyze.py output/ne2_k_sweep_*.json

Reads the sweep index produced by ne2_k_sweep.sh, then for each K
reads the per-K pt_e2 JSON and tabulates:
  K  raw_best  fmm  pt_seconds  final_replica_scores  final_fmm
"""

import json
import re
import sys
from pathlib import Path


W = 16
H = 16
BORDER = 0


def load_forbidden(path):
    return [tuple(p) for p in json.load(open(path))]


def fmm_from_url(url, forbidden):
    """Compute forbidden-mismatch count from bucas URL given a top-K list."""
    m = re.search(r'board_edges=([a-z]+)', url or '')
    if not m:
        return None
    blob = m.group(1)
    quads = [
        tuple(ord(blob[pos * 4 + i]) - ord('a') for i in range(4))
        for pos in range(W * H)
    ]
    fmm = 0
    for typ, pos in forbidden:
        if typ == 'h':
            a, b = quads[pos][1], quads[pos + 1][3]
        else:
            a, b = quads[pos][2], quads[pos + W][0]
        if a == BORDER or b == BORDER:
            continue
        if a != b:
            fmm += 1
    return fmm


def main():
    if len(sys.argv) < 2:
        print("usage: ne2_analyze.py sweep.json [forbidden.json]", file=sys.stderr)
        sys.exit(1)
    sweep_path = sys.argv[1]
    forbidden_path = sys.argv[2] if len(sys.argv) > 2 else "data/forbidden_top6.json"
    forbidden = load_forbidden(forbidden_path)
    print(f"# forbidden edges (top-{len(forbidden)}): {forbidden}", file=sys.stderr)

    sweep = json.load(open(sweep_path))
    print(f"# K-sweep entries: {len(sweep)}", file=sys.stderr)

    rows = []
    for entry in sweep:
        K = entry["K"]
        pt_s = entry["pt_seconds"]
        seed = entry["seed"]
        jpath = entry["json_path"]
        if not Path(jpath).exists():
            print(f"  K={K}  json missing: {jpath}", file=sys.stderr)
            continue
        j = json.load(open(jpath))
        score = j.get("score", {}).get("matched_edges")
        url = j.get("bucas_url", "")
        # Canonical fmm from URL.
        fmm_recomputed = fmm_from_url(url, forbidden)
        details_pt = j.get("details", {}).get("pt", {})
        recorded_fmm = details_pt.get("best_board_fmm")
        replica_scores = details_pt.get("final_replica_scores", [])
        replica_fmm = details_pt.get("final_fmm", [])
        swap_rate = (details_pt.get("swap_accepts", 0) / details_pt.get("swap_proposals", 1)
                     if details_pt.get("swap_proposals", 0) > 0 else 0.0)
        rows.append({
            "K": K,
            "pt_s": pt_s,
            "score": score,
            "fmm_recomputed": fmm_recomputed,
            "fmm_recorded": recorded_fmm,
            "replica_scores": replica_scores,
            "replica_fmm": replica_fmm,
            "swap_rate": swap_rate,
            "jpath": jpath,
        })

    # Tabular output.
    print(f"\n{'K':>5}  {'best':>5}  {'fmm':>4}  {'swap%':>5}  {'cold_scores':<32}  {'cold_fmm':<24}")
    print("-" * 90)
    for r in rows:
        cs = ','.join(str(s) for s in r['replica_scores'][:4])
        cf = ','.join(str(s) for s in r['replica_fmm'][:4])
        print(f"{r['K']:>5}  {r['score']:>5}  {r['fmm_recomputed']!s:>4}  "
              f"{r['swap_rate']*100:>4.1f}%  {cs:<32}  {cf:<24}")

    # Highlights.
    print("\n=== HIGHLIGHTS ===")
    if not rows:
        print("(no rows)")
        return
    best_raw = max(rows, key=lambda r: r['score'] or 0)
    print(f"best raw: K={best_raw['K']} → {best_raw['score']}/480 (fmm={best_raw['fmm_recomputed']})")
    resolved = [r for r in rows if r['fmm_recomputed'] == 0]
    if resolved:
        best_resolved = max(resolved, key=lambda r: r['score'])
        print(f"best with fmm=0 (all {len(forbidden)} forbidden resolved): "
              f"K={best_resolved['K']} → {best_resolved['score']}/480")
        if best_resolved['score'] > 449:
            print(f"*** BROKE THE 449 PLATEAU WITH ALL TOP-{len(forbidden)} RESOLVED ***")
    else:
        print(f"no run reached fmm=0 (no all-{len(forbidden)}-resolved configurations)")

    # K vs score (signal-vs-noise).
    print("\nK → best score signal:")
    by_k = sorted([(r['K'], r['score']) for r in rows])
    for K, s in by_k:
        bar = '█' * (s - 440) if s and s > 440 else ''
        print(f"  K={K:>4}  {s!s:>5}  {bar}")


if __name__ == "__main__":
    main()
