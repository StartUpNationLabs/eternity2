import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle
from f2_patch_lp import build_and_solve_base
for f in ['small/g4_c5_s1.csv','small/g5_c8_s1.csv','small/g6_c10_s1.csv']:
    size,pieces,hints=load_puzzle(f)
    t0=time.time()
    res=build_and_solve_base(size,pieces,hints=None,integer=False)
    lp=res[0] if res else None
    print(f"{f}: base per-edge LP-UB = {lp:.3f}  ({time.time()-t0:.1f}s)")
