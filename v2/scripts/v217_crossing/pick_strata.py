#!/usr/bin/env python3
"""Stratified pick for the stage-3 penetration experiment (prereg).
Two-pass census inputs: floors.tsv (tropical, all states) +
census_counts.tsv (counting, floor<=1 + samples) + dups.tsv (paths).

Usage: pick_strata.py FLOORS.tsv COUNTS.tsv DUPS.tsv OUT.tsv
"""
import csv
import sys


def main():
    floors_p, counts_p, dups_p, out = sys.argv[1:5]
    tag2file = {}
    with open(dups_p) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            tag = r["file"].rsplit("/", 1)[-1][:-5]
            tag2file[tag] = r["file"]
    floors = {}
    with open(floors_p) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            floors[r["tag"]] = int(r["floor"])
    soft = {}
    with open(counts_p) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            soft[r["tag"]] = float(r["soft_g03"])

    def bucket(fl):
        return sorted(
            [(t, soft[t]) for t, f in floors.items() if f == fl and t in soft],
            key=lambda x: -x[1])

    f0, f1, f2 = bucket(0), bucket(1), bucket(2)
    f3 = sorted([(t, soft[t]) for t, f in floors.items()
                 if (f >= 3 or f == -1) and t in soft], key=lambda x: -x[1])
    picks = []
    picks += [(t, "f0_top", 0, s) for t, s in f0[:4]]
    if len(f0) >= 8:
        picks += [(t, "f0_bot", 0, s) for t, s in f0[-4:]]
    m = len(f1) // 2
    picks += [(t, "f1_mid", 1, s) for t, s in f1[max(0, m - 2):m + 2]]
    pool2 = f2 if len(f2) >= 4 else f2 + f3
    m = len(pool2) // 2
    picks += [(t, "f2plus_mid", 2, s) for t, s in pool2[max(0, m - 2):m + 2]]
    with open(out, "w") as fh:
        fh.write("file\tstratum\tfloor\tsoft\n")
        for t, st, b, s in picks:
            fh.write(f"{tag2file[t]}\t{st}\t{floors[t]}\t{s:.4f}\n")
    print(f"picked {len(picks)}; population floors: "
          f"f0={len(f0)} f1={len(f1)} f2={len(f2)} f3+={len(f3)}")


if __name__ == "__main__":
    main()
