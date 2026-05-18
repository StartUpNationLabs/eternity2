---
name: regin-alldiff-brouillon
description: "Vol-125 brouillon: math + pseudocode for Régin 1994 alldiff filter applied to Eternity II super-block BB&B. Written carefully to debug v6 bug (max-depth dropped from 39 -> 30 when Régin filter was active, suggesting over-removal)."
metadata:
  type: project
---

# Régin's alldiff filter — math from first principles

## The problem we model

In our super-block BB&B:

- Pieces: $P = \{0, 1, \ldots, 255\}$ (256 distinct pieces).
- Cell-slots: $\mathcal{S} = \{(\text{supercell}, \text{slot}) : \text{supercell} \in \text{8} \times \text{8}, \text{slot} \in \{TL, TR, BL, BR\}\}$, so $|\mathcal{S}| = 256$.
- Bipartite graph $G_B = (P \cup \mathcal{S}, E)$. Edge $(p, s) \in E$ iff piece $p$ can occupy cell-slot $s$ (i.e., there exists at least one currently-live block in the supercell's alphabet that uses $p$ in $s$).

Each piece must be placed at exactly one cell-slot, and each cell-slot must hold exactly one piece. We want a perfect matching $M^* \subseteq E$ of size 256.

A piece $p$ being placed at slot $s$ corresponds to selecting some block at the supercell of $s$ that uses $p$ in $s$. **The selected block also fixes which pieces go to the other 3 slots of the supercell.** This is more constrained than pure alldiff — the bipartite edges aren't independent. But Régin's filter still gives a NECESSARY condition: if any edge is in no max matching of the bipartite, it can't be used.

## Régin's theorem (1994)

Given:
- Bipartite graph $G_B = (X \cup Y, E)$ (here $X = P$, $Y = \mathcal{S}$).
- A maximum matching $M$ of $G_B$.

Construct a **directed** graph $G_D = (X \cup Y, E_D)$:
- For each edge $(x, y) \in M$: add directed edge $y \to x$.
- For each edge $(x, y) \in E \setminus M$: add directed edge $x \to y$.

If $|M|$ doesn't saturate $X$ (we need it to: $|M| = 256$):
- Add a sink $t$. For each unmatched $x$: edge $x \to t$.
- (And similarly for unmatched $y$ if needed.)

**Theorem (Régin 1994, building on Berge 1957):**
An edge $e \in E$ belongs to some maximum matching of $G_B$ iff one of:
(a) $e \in M$, OR
(b) Both endpoints of $e$ are in the **same SCC** of $G_D$, OR
(c) $e$ lies on an alternating path starting at an unmatched vertex (this is what the sink-edge captures).

In our case $|M| = |X| = 256$ (perfect), so condition (c) doesn't apply (no unmatched vertices on either side).

**Filter rule (vital edge test):**
An edge $(x, y) \in E$ with $(x, y) \notin M$ is **removable** (not in any max matching) iff $x$ and $y$ are in **different** SCCs of $G_D$.

## What I coded (and what's likely wrong)

```
Build adj[]:
  for p in 0..256:
    matched_cs = hk_match_p[p]
    for cs in hk_piece_adj[p]:  // all cell-slots adjacent to p in G_B
      if cs == matched_cs:
        adj[cs+256] -> push(p)       # cs -> p, matching edge
      else:
        adj[p] -> push(cs+256)       # p -> cs, non-matching edge

Tarjan SCC on adj.

For each p, for each cs in hk_piece_adj[p]:
  if cs != matched_cs and scc_id[p] != scc_id[cs+256]:
    remove all blocks at (sr, sc) using piece p in slot   # SUPPOSED to be wrong?
```

## The likely bug

**Régin filter removes (piece, cell-slot) bipartite edges**, not blocks. The connection:
- Bipartite edge $(p, s)$ alive iff `slot_block_count[p, s] > 0`.
- To "remove edge $(p, s)$" → remove all blocks at supercell of $s$ that use $p$ in $s$'s slot.

I do exactly that. So semantically correct.

**However**, the filter should ONLY remove edges that **GUARANTEED not to be in any max matching**. Suppose I am wrong about SCCs and falsely conclude an edge is removable. Then I delete blocks that ARE part of valid solutions. **Over-removal** → spurious UNSAT detected at shallow depths → max-depth drops.

Observed behavior: v6 max-depth = 30 (much worse than v5's 40). Strong evidence of over-removal.

## Most likely SCC bug

Iterative Tarjan is tricky. Let me re-derive the parent-propagation:

Recursive Tarjan:
```
def tarjan(v):
  index[v] = lowlink[v] = next_idx; next_idx += 1
  stack.push(v); onstack[v] = true
  for w in adj[v]:
    if index[w] == -1:
      tarjan(w)
      lowlink[v] = min(lowlink[v], lowlink[w])    # AFTER recursive call
    elif onstack[w]:
      lowlink[v] = min(lowlink[v], index[w])      # NOT lowlink[w]
  if lowlink[v] == index[v]:
    pop SCC starting at v
```

Iterative version with manual stack:
```
push (v, iter=0) onto call_stack
loop:
  (v, pos) = call_stack.top()
  neighbors = adj[v]
  if pos < len(neighbors):
    w = neighbors[pos]
    call_stack.top().pos = pos + 1
    if index[w] == -1:
      # Simulate recursive call.
      index[w] = lowlink[w] = next_idx; next_idx += 1
      stack.push(w); onstack[w] = true
      call_stack.push((w, 0))
      # Continue loop; next iteration picks up at w.
    elif onstack[w]:
      lowlink[v] = min(lowlink[v], index[w])
  else:
    # Done with v.
    call_stack.pop()
    if lowlink[v] == index[v]:
      pop SCC
    # Propagate v's lowlink to parent.
    if call_stack non-empty:
      parent = call_stack.top().node
      lowlink[parent] = min(lowlink[parent], lowlink[v])
```

My code (re-reading):
```rust
} else {
    // Finish node.
    call_stack.pop();
    let nu = node as usize;
    if self.scc_lowlink[nu] == self.scc_index[nu] {
        loop {
            let w = self.scc_stack.pop().unwrap();
            self.scc_onstack[w as usize] = false;
            self.scc_id[w as usize] = next_scc;
            if w == node { break; }
        }
        next_scc += 1;
    }
    // Propagate lowlink to parent (if any).
    if let Some(&(parent, _)) = call_stack.last() {
        let pu = parent as usize;
        if self.scc_lowlink[nu] < self.scc_lowlink[pu] {
            self.scc_lowlink[pu] = self.scc_lowlink[nu];
        }
    }
}
```

**This looks right.** Each node propagates its lowlink to its parent on finish.

Actually wait — there's a subtle issue. When I "simulate recursive call" by pushing a new child:
```rust
self.scc_index[w as usize] = next_idx;
self.scc_lowlink[w as usize] = next_idx;
next_idx += 1;
self.scc_stack.push(w);
self.scc_onstack[w as usize] = true;
call_stack.push((w, 0));
```

After this, the **outer loop** picks up at the new top (which is w). The current node v's pos field has already been advanced (`pos+1`). Good. But v's `lowlink` will only be updated when w **finishes** and propagates. So between pushing w and finishing w, v's lowlink hasn't seen w's lowlink yet. That's fine for the loop logic.

Now the issue: in the recursive version, `lowlink[v] = min(lowlink[v], lowlink[w])` runs **AFTER** the recursive call returns. In my iterative, the equivalent is "v's parent gets w's lowlink propagated when w finishes". But wait — when w finishes, my code propagates to "parent" = call_stack.top() which is v (since v is now back on top). So `lowlink[v] = min(lowlink[v], lowlink[w])`. ✓

Hmm. The algorithm seems right. Let me check another thing: my `hk_piece_adj` represents the bipartite edges. After running HK, this list should be the SAME bipartite edges. Then for SCC, I split into matching vs non-matching.

Actually wait — I JUST noticed. `hk_match_p[p]` is `i16` and `hk_piece_adj[p]` stores `u16`. In:
```rust
let matched_cs = self.hk_match_p[p as usize];  // i16
...
if cs as i16 == matched_cs { continue; }   // cs is u16, cast to i16
```

If matching is valid, matched_cs is in 0..256 so i16 == u16-cast works. Fine.

## Possible bug I missed

OK, let me try yet another angle. What if the SCC implementation is correct, but my INTERPRETATION is wrong?

Régin filter: "edge $(x, y) \notin M$ is removable iff $x, y$ in **different** SCCs."

My code:
```rust
if cs != matched_cs and scc_id[p] != scc_id[256+cs]:
    remove edge (p, cs)
```

That matches. So if SCCs are correct, removal is correct.

**Unless**: the graph $G_D$ I built has a different structure than what Régin's theorem requires. Let me re-verify direction:
- Régin: matching edges $y \to x$ (cell-slot back to piece).
- Régin: non-matching $x \to y$ (piece to cell-slot).

My code:
- Matching: `adj[256 + cs].push(p)` = adj[y].push(x) → directed edge y → x. ✓
- Non-matching: `adj[p].push(256 + cs)` = adj[x].push(y) → directed edge x → y. ✓

Direction looks right.

## What else could be wrong?

Memory layout: `hk_piece_adj` is rebuilt by `build_hk_adjacency` based on `slot_block_count`. Could there be a stale-data issue?

Let me trace: `regin_filter` → `hopcroft_karp` → `build_hk_adjacency` (clears + repopulates `hk_piece_adj`) → HK matches. Then `regin_filter` continues, builds local adj from `hk_piece_adj`. The `hk_piece_adj` should reflect current `slot_block_count`. OK.

Then `regin_filter` calls `self.remove()` which decrements `slot_block_count`. After regin_filter, `slot_block_count` no longer matches `hk_piece_adj` — but that doesn't matter, we're done with that call. The NEXT regin_filter call will rebuild.

## Hypothesis: ITERATIVE TARJAN PROPAGATION TIMING

Let me trace a small example. Suppose: A → B → C → A (cycle of 3).
- root=A. push (A, 0). index[A]=0, lowlink[A]=0.
- Loop: A at pos 0, neighbor=B (unvisited).
  - pos→1.
  - index[B]=1, lowlink[B]=1. push (B, 0).
- Loop: B at pos 0, neighbor=C (unvisited).
  - pos→1.
  - index[C]=2, lowlink[C]=2. push (C, 0).
- Loop: C at pos 0, neighbor=A (on stack, index 0).
  - pos→1.
  - lowlink[C] = min(2, 0) = 0.
- Loop: C at pos 1, no more neighbors.
  - Pop C. lowlink[C]=0 != index[C]=2, so no SCC.
  - Propagate: parent=B (call_stack top). lowlink[B] = min(1, 0) = 0.
- Loop: B at pos 1, no more neighbors.
  - Pop B. lowlink[B]=0 != index[B]=1, so no SCC.
  - Propagate: parent=A. lowlink[A] = min(0, 0) = 0.
- Loop: A at pos 1, no more neighbors.
  - Pop A. lowlink[A]=0 == index[A]=0, so SCC!
  - Pop stack: C, B, A. SCC = {A, B, C}. ✓

My code does this correctly.

OK so the algorithm seems right. The bug must be elsewhere. Let me run the test with asserts:

Actually wait — I just realized. In my v6 test (with assertion), I might be running ASSERT-INSTRUMENTED but the slowdown to 1.5 nodes/s might be because I added 256*2 assertions per regin call. Let me think differently.

## Going forward

Rather than debug v6 in place, let me:
1. **Add a CORRECTNESS TEST**: feed the bipartite graph into a known-good SCC (e.g., write a recursive simple version) and compare.
2. **Add INSTRUMENTATION**: log "blocks removed per regin call" and "depth-trajectory". If first regin removes a LOT (more than ALC-3 already did), that suggests over-removal.
3. **TEMPORARILY disable removal**: just run regin's SCC computation but DON'T remove anything. Compare to check-only. If same behavior, the over-removal IS the bug.

Step 3 is the cheapest diagnostic. Let me do that.

## Next-day TODO

- v6.1: same as v6 but `regin_filter` skips the actual `self.remove()` call. Should behave identically to `check_alldiff` (since no blocks removed) — confirms SCC isn't corrupting state.
- v6.2: same as v6 but with a recursive (small-input only?) reference SCC. If SCC results match, SCC isn't the bug.
- v6.3: only remove ONE edge per call (to limit damage). If max-depth recovers, the issue is volume of removal not the algorithm.
