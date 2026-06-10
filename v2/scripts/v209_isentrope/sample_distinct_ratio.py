"""
ISENTROPE Variant-B-by-sampling (vol-209). Exact distinct-count is exponential
(n=3 distinct DFS = hours). Instead estimate the SCARCITY RATIO
   rho(n) = W_distinct(n) / W_reusable(n) = P(uniform random valid reusable n×n
            block uses ALL-DISTINCT pieces)
by UNIFORMLY sampling valid reusable blocks (exact backward-trace from the forward
DP) and checking the distinct fraction. Gives rho(n) with a binomial CI, cheaply,
for n=3,4,5,6 — the entropy-theoretic signature of piece-theft / the wall.

Uniform sampling: forward DP stores per-cell layer state->count. Backward trace:
sample the final layer state ∝ count, then at each cell (reverse order) sample the
incoming (state, placement) ∝ (count of predecessor state that leads here). We
implement by storing, at each cell step, for each NEW state the list of
(prev_state, placement) contributions with their weights, then sample backward.
"""
import sys, os, collections, math, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W

SIZE, PIECES, HINTS = load_puzzle()
FREE = -1

# interior placements WITH piece id (need id for distinctness check)
PL = []  # (pid, N, E, S, W)
for pid in range(len(PIECES)):
    if BORDER in PIECES[pid]:
        continue
    seen=set()
    for r in range(4):
        ed = rot_edges(PIECES[pid], r)
        if ed in seen: continue
        seen.add(ed)
        PL.append((pid, ed[N], ed[E], ed[S], ed[W]))
by_n = collections.defaultdict(list)
for p in PL: by_n[p[1]].append(p)
ALLP = PL

def successors(state, x, n):
    """yield (placement, next_state) for filling cell at column x from `state`."""
    profile, pend = state
    needN = profile[x]; needW = pend
    cands = ALLP if needN==FREE else by_n[needN]
    for pl in cands:
        pid,pn,pe,ps,pw = pl
        if needW!=FREE and pw!=needW: continue
        nprof = profile[:x] + (ps,) + profile[x+1:]
        npend = pe if x<n-1 else FREE
        yield pl, (nprof, npend)

def suffix_counts(n):
    """suffix[k][state] = number of ways to complete cells k..n*n-1 from `state`.
       Computed backward. suffix[n*n][*] = 1 (empty completion)."""
    total = n*n
    suffix = [None]*(total+1)
    # we only need states reachable; compute forward reachable sets per cell first.
    start = ((FREE,)*n, FREE)
    reach = [set() for _ in range(total+1)]
    reach[0].add(start)
    for k in range(total):
        x = k % n
        for st in reach[k]:
            for _pl, ns in successors(st, x, n):
                reach[k+1].add(ns)
    # backward suffix counts
    suffix[total] = {st: 1 for st in reach[total]}
    for k in range(total-1, -1, -1):
        x = k % n
        sc = {}
        nxt = suffix[k+1]
        for st in reach[k]:
            tot = 0
            for _pl, ns in successors(st, x, n):
                tot += nxt.get(ns, 0)
            sc[st] = tot
        suffix[k] = sc
    Wre = suffix[0][start]
    return suffix, start

def sample_block(n, suffix, start, rng):
    """Forward uniform sample weighted by suffix counts. Returns list of pids."""
    total = n*n
    pids=[None]*total
    st = start
    for k in range(total):
        x = k % n
        opts=[]; wsum=0
        nxt = suffix[k+1]
        for pl, ns in successors(st, x, n):
            w = nxt.get(ns, 0)
            if w==0: continue
            opts.append((pl, ns, w)); wsum+=w
        if wsum==0: return None
        r = rng.random()*wsum; acc=0; chosen=None
        for (pl,ns,w) in opts:
            acc+=w
            if r<=acc: chosen=(pl,ns); break
        if chosen is None: chosen=(opts[-1][0],opts[-1][1])
        pids[k]=chosen[0][0]; st=chosen[1]
    return pids

def estimate_ratio(n, nsamples=20000, seed=12345):
    suffix, start = suffix_counts(n)
    Wre = suffix[0][start]
    rng = random.Random(seed)
    distinct=0; ok=0
    for _ in range(nsamples):
        pids = sample_block(n, suffix, start, rng)
        if pids is None: continue
        ok+=1
        if len(set(pids))==len(pids): distinct+=1
    rho = distinct/ok if ok else float('nan')
    se = math.sqrt(rho*(1-rho)/ok) if ok else 0
    return Wre, rho, 1.96*se, ok

if __name__=="__main__":
    print(f"interior placements: {len(PL)}", flush=True)
    print("n  W_reusable  rho=B/A(distinct frac)  95%CI  samples", flush=True)
    # exact anchors: n=1 rho=1.0, n=2 rho=0.8922
    for n in [2,3,4,5]:
        Wre, rho, ci, ok = estimate_ratio(n, nsamples=20000)
        # implied S_distinct = log10(Wre*rho)
        Sdist = math.log10(Wre*rho) if rho>0 else float('-inf')
        print(f"{n}  {Wre}  rho={rho:.4f} ±{ci:.4f}  S_dist≈{Sdist:.3f} (S/n²={Sdist/(n*n):.4f})  n_ok={ok}", flush=True)
