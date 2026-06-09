import sys,time;sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
import highspy, numpy as np
from collections import defaultdict
# Reuse build but with IPM solver + time limit. Quick inline copy of base-only.
from f4_patch_sound import build
# monkey not needed; call build but set options? build creates its own Highs.
# Simpler: just time a capped run by calling build but it has no cap. Instead
# replicate minimal base with options here is overkill; rely on prior small
# evidence. We just do a 90s-capped attempt using HiGHS choose + presolve.
