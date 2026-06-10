"""ISENTROPE Variant A (reusable pieces / color-grammar entropy) — own process.
Computes W_Γ(n) for n=1.. as far as tractable, writes each point as it completes."""
import sys, os, time, math, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
sys.path.insert(0, os.path.dirname(__file__))
from count_entropy import count_reusable

OUT = "scripts/v209_isentrope/output/variantA.jsonl"
open(OUT, "w").close()
print("=== Variant A: color-grammar entropy (reusable pieces) ===", flush=True)
for n in range(1, 7):
    t = time.time()
    try:
        w = count_reusable(n)
    except MemoryError:
        print(f"  n={n}: MemoryError — stop", flush=True); break
    s = math.log10(w) if w > 0 else float("-inf")
    secs = time.time() - t
    rec = {"n": n, "W": str(w), "S": s, "S_over_n2": s/(n*n), "secs": secs}
    print(f"  n={n}: W={w}  S=log10={s:.4f}  S/n^2={s/(n*n):.5f}  ({secs:.1f}s)", flush=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")
    if secs > 1200:   # if a single n took >20min, the next is hopeless
        print(f"  n={n} took {secs:.0f}s; stopping before n={n+1}", flush=True); break
print("Variant A done.", flush=True)
