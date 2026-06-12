#!/usr/bin/env python3
"""Score every banked prefix found in a labels.tsv with the crossing
oracle. Dedups (prefix_file, frame); resolves frames from
output/vol-212/frames_best/ and output/vol-213/frames_census50/.

Usage: run_sweep.py LABELS.tsv OUT.tsv
"""
import csv
import os
import sys

import crossing_oracle as X
import lp_prefix_score as L

V2 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FRAME_PATHS = {
    "strict460a": "output/vol-212/frames_best/strict460a.json",
    "strict460b": "output/vol-212/frames_best/strict460b.json",
    "gen0143": "output/vol-213/frames_census50/gen0143.json",
}


def main():
    labels, out_path = sys.argv[1], sys.argv[2]
    ctx = X.build_ctx()
    rims = {f: L.rim_targets_from_frame(os.path.join(V2, p), ctx[0])
            for f, p in FRAME_PATHS.items()}
    seen = {}
    with open(labels) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            seen[(row["prefix_file"], row["frame"])] = row["tag"]
    items = sorted(seen.items())
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as fh:
            done = {r["tag"] for r in csv.DictReader(fh, delimiter="\t")}
    mode = "a" if done else "w"
    with open(out_path, mode) as out:
        if not done:
            out.write("tag\tframe\tdepth\tsoft_g03\tbmin\tlog_at_bmin"
                      "\tn_pool\tprefix_breaks\tms\n")
        skipped = []
        for i, ((pf, frame), tag) in enumerate(items):
            if tag in done:
                continue
            try:
                r = X.score_prefix(ctx, rims[frame], os.path.join(V2, pf))
            except AssertionError as ex:
                skipped.append(tag)
                print(f"SKIP {tag}: {ex}", file=sys.stderr, flush=True)
                continue
            lb = r["logs"][r["bmin"]] if r["bmin"] >= 0 else float("-inf")
            depth = r["n_placed"]
            out.write(f"{tag}\t{frame}\t{depth}\t{r['soft']:.4f}\t{r['bmin']}"
                      f"\t{lb:.3f}\t{r['n_pool']}\t{r['prefix_breaks']}"
                      f"\t{r['ms']:.0f}\n")
            out.flush()
            if i % 25 == 0:
                print(f"{i}/{len(items)}", file=sys.stderr, flush=True)
        print(f"done; skipped {len(skipped)} (rows 0-9 incomplete): "
              f"{skipped}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
