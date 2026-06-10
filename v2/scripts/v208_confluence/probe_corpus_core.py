"""
CONFLUENCE premise — corpus-wide shared scarce-demand core (vol-208).
Confirm the ~24-shared finding is universal across the ≥458 corpus, not a
2-board artifact. Also measure a control band (440-457) to test whether the
shared core GROWS with score (=> it's a real attractor toward high basins).
"""
import sys, os, glob, collections, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
import e2lib as E

SIZE, PIECES, HINTS = E.load_puzzle()
NP=len(PIECES); N,Eh,S,W=0,1,2,3; BORDER=65535

servers=collections.defaultdict(set)
for pid in range(NP):
    base=PIECES[pid]; seen=set()
    for r in range(4):
        ed=E.rot_edges(base,r); key=(ed[N],ed[W])
        if key in seen: continue
        seen.add(key); servers[key].add(pid)
uniq={k:next(iter(v)) for k,v in servers.items()
      if k[0]!=BORDER and k[1]!=BORDER and len(v)==1}
print(f"unique-server interior demands: {len(uniq)}")

def activated_set(board):
    s=set()
    for y in range(SIZE):
        for x in range(SIZE):
            pos=y*SIZE+x
            if pos not in board: continue
            pid,r=board[pos]; ed=E.rot_edges(PIECES[pid],r)
            c1,c2=ed[N],ed[W]
            if c1==BORDER or c2==BORDER: continue
            if (c1,c2) in uniq: s.add((c1,c2))
    return s

def load_score_from_name(p):
    m=re.match(r'(\d+)_', os.path.basename(p))
    return int(m.group(1)) if m else None

files=glob.glob("database-400-480/*.json")
bands={'>=458':[], '450-457':[], '440-449':[], '420-439':[]}
for f in files:
    sc=load_score_from_name(f)
    if sc is None: continue
    if sc>=458: bands['>=458'].append(f)
    elif sc>=450: bands['450-457'].append(f)
    elif sc>=440: bands['440-449'].append(f)
    elif sc>=420: bands['420-439'].append(f)

def analyze_band(name, fs, maxn=400):
    fs=fs[:maxn]
    acts=[]; ok=0
    for f in fs:
        try:
            board,d=E.load_board(f)
            # re-score to filter fakes
            m,t=E.score_board(SIZE,PIECES,board)
            sc=load_score_from_name(f)
            if abs(m-sc)>2:  # claimed vs independent mismatch => skip (fake/dup)
                continue
            acts.append(activated_set(board)); ok+=1
        except Exception as e:
            continue
    if not acts:
        print(f"{name}: no valid boards"); return None
    # per-board activation count
    counts=[len(a) for a in acts]
    counts.sort()
    # demand frequency across the band
    freq=collections.Counter()
    for a in acts:
        for dem in a: freq[dem]+=1
    nb=len(acts)
    # core = demands present in >= 80% of boards
    core80={dem for dem,c in freq.items() if c>=0.8*nb}
    core50={dem for dem,c in freq.items() if c>=0.5*nb}
    print(f"\n=== {name}: {nb} valid boards ===")
    print(f"  activated/board: min {counts[0]}, median {counts[len(counts)//2]}, max {counts[-1]}")
    print(f"  demands in >=80% of boards (hard core): {len(core80)}")
    print(f"  demands in >=50% of boards: {len(core50)}")
    print(f"  most-common demands (top 10 freq/{nb}): "
          f"{[(d, c) for d,c in freq.most_common(10)]}")
    return core80, core50, set(freq.keys())

r458=analyze_band('>=458', bands['>=458'])
r450=analyze_band('450-457', bands['450-457'])
r440=analyze_band('440-449', bands['440-449'])
r420=analyze_band('420-439', bands['420-439'])

if r458 and r440:
    c458=r458[0]; c440=r440[0]
    print(f"\nCORE GROWTH: >=458 hard-core size {len(c458)} vs 440-449 {len(c440)}")
    print(f"  core(>=458) demands also in 440-449 union: {len(c458 & r440[2])}/{len(c458)}")
