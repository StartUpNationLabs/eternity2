import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from pysat.card import CardEnc, EncType
from collections import defaultdict
size,pieces,hints=load_puzzle()
NP=len(pieces)
def bbs(c):
    x=c%size;y=c//size;s=set()
    if y==0:s.add(N)
    if y==size-1:s.add(S)
    if x==0:s.add(W)
    if x==size-1:s.add(E)
    return s
def solve(cells,pool,fo,use_card=True):
    cellset=set(cells);cand={};var={};nv=0
    for c in cells:
        bb=bbs(c);lst=[]
        for p in pool:
            for r in range(4):
                ed=rot_edges(pieces[p],r)
                if {i for i in range(4) if ed[i]==BORDER}!=bb:continue
                ok=True
                for s,col in fo.get(c,{}).items():
                    if ed[s]!=col:ok=False;break
                if ok:lst.append((p,r,ed))
        cand[c]=lst
        for t in lst:nv+=1;var[(c,t[0],t[1])]=nv
    top=[nv]
    def newv():top[0]+=1;return top[0]
    wcnf=WCNF()
    for c in cells:
        lits=[var[(c,t[0],t[1])] for t in cand[c]]
        if not lits:return None,0
        if use_card:
            cnf=CardEnc.equals(lits,1,top_id=top[0],encoding=EncType.seqcounter)
            top[0]=max(top[0],cnf.nv)
            for cl in cnf.clauses:wcnf.append(cl)
        else:
            wcnf.append(lits)
            for a in range(len(lits)):
                for b in range(a+1,len(lits)):wcnf.append([-lits[a],-lits[b]])
    bypiece=defaultdict(list)
    for c in cells:
        for t in cand[c]:bypiece[t[0]].append(var[(c,t[0],t[1])])
    for p,lits in bypiece.items():
        if len(lits)<2:continue
        if use_card:
            cnf=CardEnc.atmost(lits,1,top_id=top[0],encoding=EncType.seqcounter)
            top[0]=max(top[0],cnf.nv)
            for cl in cnf.clauses:wcnf.append(cl)
        else:
            for a in range(len(lits)):
                for b in range(a+1,len(lits)):wcnf.append([-lits[a],-lits[b]])
    edges=[]
    for c in cells:
        x=c%size;y=c//size
        if x+1<size and c+1 in cellset:edges.append((c,E,c+1,W))
        if y+1<size and c+size in cellset:edges.append((c,S,c+size,N))
    nint=len(edges)
    for (c1,s1,c2,s2) in edges:
        for t1 in cand[c1]:
            for t2 in cand[c2]:
                if t1[0]==t2[0]:continue
                if t1[2][s1]!=t2[2][s2]:
                    wcnf.append([-var[(c1,t1[0],t1[1])],-var[(c2,t2[0],t2[1])]],weight=1)
    t0=time.time()
    with RC2(wcnf) as rc2:
        m=rc2.compute();cost=rc2.cost
    return nint-cost,time.time()-t0
pool=set(p for p in range(NP) if sum(1 for c in pieces[p] if c==BORDER)==0)
for (h,w) in [(2,2),(2,3),(3,3),(2,4),(4,4)]:
    cells=[(1+dy)*size+(1+dx) for dy in range(h) for dx in range(w)]
    for card in [False,True]:
        r,secs=solve(cells,pool,{},use_card=card)
        print(f"{h}x{w} card={card}: internal={r} {secs:.2f}s")
