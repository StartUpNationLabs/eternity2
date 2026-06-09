"""MOSAIC with BLOCK-LEVEL BACKTRACKING. Search over exact block solutions.
Each block level keeps an enumerator of MaxSAT solutions (best-first via RC2 +
blocking clauses). On an infeasible / exhausted block, backtrack to the previous
level and pull its next solution (freeing different pieces).

This is 'backtracking search over EXACT blocks' — coarse (16 levels) but each
node is a provably-optimal block fill.
"""
import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from collections import defaultdict

size,pieces,hints=load_puzzle()
NP=len(pieces)

def board_border_sides(c):
    x=c%size;y=c//size;s=set()
    if y==0:s.add(N)
    if y==size-1:s.add(S)
    if x==0:s.add(W)
    if x==size-1:s.add(E)
    return s

class BlockSolver:
    """Enumerates MaxSAT solutions of one block, best-first, given fixed pool+boundary."""
    def __init__(self, cells, pool, fixed_outer, min_internal):
        self.cells=cells; self.cellset=set(cells)
        self.cand={}; self.var={}; nv=0
        for c in cells:
            bb=board_border_sides(c); lst=[]
            for p in pool:
                for r in range(4):
                    ed=rot_edges(pieces[p],r)
                    bs={i for i in range(4) if ed[i]==BORDER}
                    if bs!=bb: continue
                    ok=True
                    for side,col in fixed_outer.get(c,{}).items():
                        if ed[side]!=col: ok=False;break
                    if not ok: continue
                    lst.append((p,r,ed))
            self.cand[c]=lst
            for (p,r,ed) in lst: nv+=1; self.var[(c,p,r)]=nv
        self.feasible=all(self.cand[c] for c in cells)
        self.min_internal=min_internal
        self.nint=0
        self.rc2=None
        if self.feasible:
            self._build()
    def _build(self):
        wcnf=WCNF()
        for c in self.cells:
            lits=[self.var[(c,p,r)] for (p,r,ed) in self.cand[c]]
            wcnf.append(lits)
            for a in range(len(lits)):
                for b in range(a+1,len(lits)): wcnf.append([-lits[a],-lits[b]])
        bypiece=defaultdict(list)
        for c in self.cells:
            for (p,r,ed) in self.cand[c]: bypiece[p].append(self.var[(c,p,r)])
        for p,lits in bypiece.items():
            for a in range(len(lits)):
                for b in range(a+1,len(lits)): wcnf.append([-lits[a],-lits[b]])
        edges=[]
        for c in self.cells:
            x=c%size;y=c//size
            if x+1<size and (c+1) in self.cellset: edges.append((c,E,c+1,W))
            if y+1<size and (c+size) in self.cellset: edges.append((c,S,c+size,N))
        self.nint=len(edges)
        for (c1,s1,c2,s2) in edges:
            for (p1,r1,e1) in self.cand[c1]:
                for (p2,r2,e2) in self.cand[c2]:
                    if p1==p2: continue
                    if e1[s1]!=e2[s2]:
                        wcnf.append([-self.var[(c1,p1,r1)],-self.var[(c2,p2,r2)]],weight=1)
        self.wcnf=wcnf
        self.rc2=RC2(wcnf)
        self.maxv=self.var and max(self.var.values()) or 0
    def next(self):
        """Return next solution (assign, internal_matched) best-first, or None.
        Only returns solutions with internal_matched >= min_internal."""
        if not self.feasible or self.rc2 is None: return None
        while True:
            model=self.rc2.compute()
            if model is None: 
                self.rc2.delete(); self.rc2=None; return None
            cost=self.rc2.cost
            internal=self.nint-cost
            if internal < self.min_internal:
                self.rc2.delete(); self.rc2=None; return None  # all further worse
            mset=set(v for v in model if v>0); assign={}
            for c in self.cells:
                for (p,r,ed) in self.cand[c]:
                    if self.var[(c,p,r)] in mset: assign[c]=(p,r)
            # add blocking clause to exclude THIS placement next time
            block=[-self.var[(c,assign[c][0],assign[c][1])] for c in self.cells]
            self.rc2.add_clause(block)
            return assign, internal
    def close(self):
        if self.rc2 is not None: self.rc2.delete(); self.rc2=None

def run(BS=4, min_internal_per_block=None, node_budget=200, time_budget=600, verbose=True):
    nb=size//BS
    blocks=[(br,bc) for br in range(nb) for bc in range(nb)]
    ncells_block=BS*BS
    nint_full = 2*BS*(BS-1)
    if min_internal_per_block is None:
        min_internal_per_block = nint_full  # require perfect blocks first
    t0=time.time(); nodes=[0]
    # stack of (solver, assign, used_set_added)
    place=[None]*(size*size); pe=[None]*(size*size); used=[False]*NP
    stack=[]
    best_board=[None]; best_score=[-1]
    def fixed_outer_for(cells):
        fo=defaultdict(dict)
        for c in cells:
            x=c%size;y=c//size
            if y>0 and place[c-size] is not None: fo[c][N]=pe[c-size][S]
            if x>0 and place[c-1] is not None: fo[c][W]=pe[c-1][E]
        return fo
    def cells_of(bi):
        br,bc=blocks[bi]
        return [ (br*BS+dy)*size+(bc*BS+dx) for dy in range(BS) for dx in range(BS)]
    def push_block(bi, min_int):
        cells=cells_of(bi)
        pool=set(p for p in range(NP) if not used[p])
        solver=BlockSolver(cells,pool,fixed_outer_for(cells),min_int)
        return solver
    def apply(assign):
        for c,(p,r) in assign.items():
            place[c]=(p,r); pe[c]=rot_edges(pieces[p],r); used[p]=True
    def unapply(assign):
        for c in assign: 
            p=place[c][0]; used[p]=False; place[c]=None; pe[c]=None
    # iterative DFS over blocks
    bi=0
    cur_min=min_internal_per_block
    solver=push_block(0, cur_min)
    while True:
        if time.time()-t0>time_budget:
            if verbose: print(f"[time budget hit at block {bi}]"); break
        nxt=solver.next() if solver else None
        if nxt is None:
            # backtrack
            solver.close() if solver else None
            if not stack:
                if verbose: print("search exhausted at root"); break
            bi-=1
            solver, assign = stack.pop()
            unapply(assign)
            continue
        assign, internal = nxt
        nodes[0]+=1
        apply(assign)
        if bi==len(blocks)-1:
            # complete board
            matched=0
            for c in range(size*size):
                x=c%size;y=c//size
                if x+1<size and pe[c][E]==pe[c+1][W]:matched+=1
                if y+1<size and pe[c][S]==pe[c+size][N]:matched+=1
            if matched>best_score[0]:
                best_score[0]=matched; best_board[0]=[place[c] for c in range(size*size)]
                if verbose: print(f"  COMPLETE board matched={matched}/480 (nodes={nodes[0]}, {time.time()-t0:.0f}s)")
            unapply(assign)
            if nodes[0]>=node_budget: break
            continue
        # descend
        stack.append((solver, assign))
        bi+=1
        solver=push_block(bi, cur_min)
        if verbose and bi<=3: print(f"  -> block {bi} (depth), nodes={nodes[0]}, {time.time()-t0:.0f}s")
        if nodes[0]>=node_budget:
            if verbose: print(f"[node budget {node_budget} hit]"); break
    return best_score[0], best_board[0], nodes[0], time.time()-t0

if __name__=="__main__":
    BS=int(sys.argv[1]) if len(sys.argv)>1 else 4
    mi=int(sys.argv[2]) if len(sys.argv)>2 else (2*BS*(BS-1))  # default perfect blocks
    tb=float(sys.argv[3]) if len(sys.argv)>3 else 300
    print(f"MOSAIC-BT BS={BS} min_internal_per_block={mi}/{2*BS*(BS-1)} time_budget={tb}s")
    sc,board,nodes,secs=run(BS=BS, min_internal_per_block=mi, time_budget=tb, node_budget=100000)
    print(f"\nBEST matched={sc}/480  nodes={nodes}  {secs:.0f}s")
