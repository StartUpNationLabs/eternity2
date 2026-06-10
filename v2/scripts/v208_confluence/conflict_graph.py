"""
Scarce-demand conflict structure (vol-208 CONFLUENCE).
The 121 unique-server (N,W) demands have HARD piece-sharing conflicts:
demand A and B conflict if they share their unique server piece (can't both be
realized - one piece, two cells). Build that conflict graph, find:
 - connected components / mutual-exclusion groups,
 - the max independent set size (= max # piece-distinct scarce demands realizable
   from the piece-sharing constraint ALONE),
 - compare to the ~31-32 demands high boards actually activate.

This is a NECESSARY condition: a board can realize at most one demand per
mutual-exclusion group. If MIS >> 31, piece-sharing isn't the binding constraint
(edge-consistency of realizing cells is). If MIS ~ 31, it nearly explains the cap.
"""
import sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
import e2lib as E
SIZE,PIECES,HINTS=E.load_puzzle(); NP=len(PIECES); N,Eh,S,W=0,1,2,3; BORDER=65535

servers=collections.defaultdict(set)
for pid in range(NP):
    base=PIECES[pid]; seen=set()
    for r in range(4):
        ed=E.rot_edges(base,r); key=(ed[N],ed[W])
        if key in seen: continue
        seen.add(key); servers[key].add(pid)
uniq={k:next(iter(v)) for k,v in servers.items()
      if k[0]!=BORDER and k[1]!=BORDER and len(v)==1}
demands=list(uniq.keys())
D=len(demands); print(f"unique-server demands D={D}")

# piece -> demands it uniquely serves
p2d=collections.defaultdict(list)
for dem,pid in uniq.items(): p2d[pid].append(dem)

# mutual-exclusion groups = demands sharing a unique server
groups=[ds for ds in p2d.values() if len(ds)>=1]
mxgroups=[ds for ds in p2d.values() if len(ds)>=2]
print(f"mutual-exclusion groups (>=2 demands/piece): {len(mxgroups)}")
# Max independent set under piece-sharing: pick 1 per group, all singletons free.
# Since each demand maps to exactly one piece, the conflict graph is a DISJOINT
# union of cliques (one clique per piece). MIS of disjoint cliques = #cliques.
n_cliques=len(p2d)
print(f"#distinct unique-server pieces (=cliques) = {n_cliques}")
print(f"=> MIS under piece-sharing alone = {n_cliques} "
      f"(pick 1 demand per piece). High boards activate ~31-32.")
print(f"   So piece-sharing caps scarce-demand realization at {n_cliques}, "
      f"NOT the binding constraint (boards realize far fewer).")

# The real constraint must be edge-consistency among the CELLS realizing demands.
# Measure: for a high board, how 'spread' are the activated demands' cells, and
# do activated demands cluster (suggesting a geometric co-realization constraint)?
