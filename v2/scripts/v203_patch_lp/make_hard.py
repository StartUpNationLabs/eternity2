"""Create an unsatisfiable-perfect puzzle by perturbing a solvable one:
change ONE interior color occurrence on ONE piece to a different color, so
the perfect tiling breaks. Write new CSV (canonical id order preserved)."""
import sys, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, BORDER

def write_csv(path, size, pieces):
    with open(path,'w') as f:
        f.write(f"{size}\n")
        for (n,e,s,w) in pieces:
            def b(c): return format(65535 if c==BORDER else c,'b')
            f.write(f"{b(n)},{b(e)},{b(s)},{b(w)}\n")

src=sys.argv[1]; out=sys.argv[2]; nflip=int(sys.argv[3]) if len(sys.argv)>3 else 1
seed=int(sys.argv[4]) if len(sys.argv)>4 else 0
size,pieces,hints=load_puzzle(src)
pieces=[list(p) for p in pieces]
colors=sorted({c for p in pieces for c in p if c!=BORDER})
rng=random.Random(seed)
flipped=0; tries=0
while flipped<nflip and tries<10000:
    tries+=1
    pi=rng.randrange(len(pieces)); side=rng.randrange(4)
    if pieces[pi][side]==BORDER: continue
    new=rng.choice([c for c in colors if c!=pieces[pi][side]])
    pieces[pi][side]=new; flipped+=1
write_csv(out, size, [tuple(p) for p in pieces])
print(f"wrote {out} (flipped {flipped} interior colors from {src})")
