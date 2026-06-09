"""Shared output helper for MOSAIC: write timestamped board JSON (canonical
placement format) + Bucas URL + a CSV history row. NEVER overwrites (timestamp
in path). Bucas encoder verified vs McGavin 469 (e2lib edges [N,E,S,W],
color c -> chr('a'+c), 0=BORDER='a')."""
import os, json, time, csv
import sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from e2lib import rot_edges, BORDER

OUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")

def _bucas_letter(c):
    if c is None or c>22: return 'a'
    return chr(ord('a')+c)

def bucas_url(pieces, place, name="mosaic"):
    """place: list cell->(pid,rot) or None. Returns bucas URL."""
    edges=[]
    for cell in range(len(place)):
        if place[cell] is None:
            edges.append("aaaa")
        else:
            pid,rot=place[cell]
            e=rot_edges(pieces[pid],rot)  # [N,E,S,W]
            edges.append("".join(_bucas_letter(e[s]) for s in range(4)))
    return f"https://e2.bucas.name/#puzzle=Eternity2&board_w=16&board_h=16&board_edges={''.join(edges)}"

def save_run(pieces, place, matched, label, extra=None, ts=None):
    """Write JSON + URL + append CSV history. Returns dir path."""
    if ts is None:
        ts=time.strftime("%Y%m%dT%H%M%S")
    d=os.path.join(OUT_ROOT, f"{label}_{ts}")
    os.makedirs(d, exist_ok=True)
    placement=[{"pos":c,"piece_id":int(place[c][0]),"rotation":int(place[c][1])}
               for c in range(len(place)) if place[c] is not None]
    url=bucas_url(pieces, place, label)
    obj={"matched":int(matched),"bucas_url":url,"source":label,
         "placement":placement}
    if extra: obj.update(extra)
    with open(os.path.join(d,"board.json"),"w") as f:
        json.dump(obj,f)
    with open(os.path.join(d,"bucas_url.txt"),"w") as f:
        f.write(url+"\n")
    # append to global history CSV
    hist=os.path.join(OUT_ROOT,"history.csv")
    newfile=not os.path.exists(hist)
    with open(hist,"a",newline="") as f:
        w=csv.writer(f)
        if newfile: w.writerow(["timestamp","label","matched","dir","bucas_url"])
        w.writerow([ts,label,matched,d,url])
    return d, url
