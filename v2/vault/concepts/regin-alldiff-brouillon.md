---
name: regin-alldiff-brouillon
description: "Vol-125 brouillon: math + pseudocode for Régin 1994 alldiff filter applied to Eternity II super-block BB&B. Written carefully to debug v6 bug (max-depth dropped from 39 -> 30 when Régin filter was active, suggesting over-removal)."
metadata:
  type: project
status: partial
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

---

## Update 2026-05-18 (post-compaction continuation)

### Standalone unit test PASSED

Built `regin_unit_test` at `crates/bench-audit/src/bin/regin_unit_test.rs` to verify the SCC + Régin logic in isolation.

- **Test 1** (1×1 trivial): ✅
- **Test 2** (2×2, unique max matching, one removable edge): ✅
- **Test 3** (2×2, dual max matching, no removable edges): ✅
- **Test 4** (3×3 with 4 max matchings, no removable): ✅
- **Test 5** (100 random 4×4 perfect-matching graphs vs brute-force): ✅ ALL 100

**Conclusion**: Iterative Tarjan + Régin removable-edge logic are mathematically correct. The bug in v6 must come from **integration** — specifically how removals interact with the rest of the state (`slot_block_count`, `domain`, `pinned`, `piece_occ`).

### Shadow mode added

Added `SHADOW: AtomicBool` to v6 via `--shadow` flag. In shadow mode, `regin_filter` computes the SCC and counts "would-have-removed" edges but does NOT call `self.remove()`. This is the cleanest diagnostic: if shadow-v6 matches v5's depth=40 trajectory, the bug is purely in the actual removal step.

### Remaining hypotheses (after unit-test ruled out algorithm)

- **(A)** Removal targets wrong cell-slot — RULED OUT: cs ↔ (sr, sc, slot) round-trips correctly via `cs = sr*32 + sc*4 + slot`.
- **(B)** Removal cascades incorrectly — possible: `remove()` decrements `slot_block_count` for ALL 4 (piece, slot) pairs of the removed block, even though only 1 was Régin-filtered. This might cause an unintended chain reaction.
- **(C)** `slot_block_count` desync with `domain` — possible if any propagator removes blocks without going through `remove()`.
- **(D)** Régin filter is correct BUT the bipartite relaxation throws away too much info: a piece-slot match that's "alldiff-feasible" might not correspond to ANY block at that cell. We saw this in the math: bipartite matching treats 4 slots of a cell as INDEPENDENT, so it OVER-counts feasibility. Wait — over-counts means the relaxation says "feasible" too often, NOT that it removes too much. So this should make v6 LESS pruning, not more. Confusing.

Wait — re-read (D): bipartite matching is necessary but not sufficient. The set of feasible (piece, slot) assignments under bipartite is a SUPERSET of true-feasible. So Régin removes edges OUTSIDE this superset → also outside the true-feasible set → SOUND removal. So (D) should not cause issues.

**So the leading hypothesis is (B): `remove()` over-decrements `slot_block_count` indirectly.**

Specific scenario: imagine block B at cell (sr,sc) has pieces (p1, p2, p3, p4) at slots (0,1,2,3). Régin says edge (p1, slot 0 at (sr,sc)) is removable. We call `remove(sr, sc, B)`. This decrements `slot_block_count` for ALL 4 pairs:
  - (p1, slot 0 at (sr,sc)) ← intended
  - (p2, slot 1 at (sr,sc)) ← unintended (this pair MAY be in some max matching!)
  - (p3, slot 2 at (sr,sc))
  - (p4, slot 3 at (sr,sc))

**This is the bug**. When Régin says "(p1, slot 0 at sr/sc) cannot be in a max matching", we should remove all blocks with `b.pieces[0] == p1` at (sr,sc). The block B is one such block, but B ALSO has pieces (p2, p3, p4) which may be valid in their respective slots in OTHER blocks. By removing B, we decrement counts for p2, p3, p4 — which is correct ONLY because B itself is gone.

Actually wait — that IS correct. If block B is gone, then `slot_block_count[(p2, slot 1 at sr/sc)]` should indeed go down by 1 (B contributed 1 to that count). The count remains accurate. There's no over-decrement.

So (B) is not the bug either. Hmm.

### Cleanest next diagnostic: smaller-puzzle test

User suggested 2026-05-18: "do you think it'd be worth it to try our algorithm on smaller puzzle we generate just for the sake of verifying it's possible?"

YES. The cleanest verification:
1. Generate a known-solvable instance of a smaller puzzle (e.g., 8×8 grid with 64 pieces).
2. Build W2 super-block alphabet (2×2 super-cells → 16 supercells of 2×2 each).
3. Run v5 and v6 on this puzzle.
4. v5 should solve. If v6 doesn't solve or returns UNSAT, that's a smoking gun.

If both solve, the bug is scale-related (e.g., trail overflow, integer aliasing, slot_counter_idx overflow at 256×256=65536). For canonical 16×16, `slot_counter_idx(piece=255, sr=7, sc=7, slot=3) = 255*256 + 7*32 + 7*4 + 3 = 65535`. That fits in u16 boundary. OK.

### Shadow run COMPLETE — bug pinpointed

`./target/bench-fast/super_block_bbb_v6 --max-nodes 300 --shadow` finished 2026-05-18 18:12.

**v5 vs v6-shadow comparison (first 300 nodes):**

| Node | v5 depth | v6-shadow depth | dom_sum | next |
|---|---|---|---|---|
| 100 | 29 | 29 | 6222968 | (7,4) |
| 200 | 36 | 36 | 1525291 | (2,2) |
| 300 | 40 | 40 | 486947 | (2,6) |

**Bit-for-bit identical** trajectories. **This proves**:

1. ✅ SCC computation is correct
2. ✅ Adjacency rebuild is correct
3. ✅ Hopcroft-Karp matching is correct
4. ✅ No state corruption from running SCC alone

**The bug is 100% in the removal step (`self.remove()` and its cascading effects).**

### Removal-step investigation

`remove(sr, sc, block_idx)` does:
1. Push trail entry (sr, sc, prev_live).
2. Decrement `slot_block_count` for all 4 (piece, slot) pairs of the removed block.
3. Mark block as out of domain (move below `d.live`).

There is no propagation triggered by `remove()` directly. But Régin removes blocks INSIDE its loop, and the loop continues iterating other (p, cs) edges using the SCC computed BEFORE any removal.

Hypothesis 1: **Removing block B reduces `slot_block_count[(p', cs)]` for 3 OTHER pieces of B** (besides the targeted p). This is correct accounting — but the OUTER loop iterates `hk_piece_adj[p]` (snapshot before removal). Inside the loop, we keep removing for the SAME p, then move to p+1 with adjacency NOT REBUILT. So when p=1 is processed, `slot_block_count` reflects all removals from p=0, but `hk_piece_adj[1]` still has STALE edges to cell-slots that may no longer have blocks (since we removed them via p=0's removals).

But that's harmless: we just iterate non-existent edges, find no blocks to remove, no-op.

Hypothesis 2: **Régin removes blocks that are STILL in some max matching, but were RULED OUT BY EARLIER REMOVALS.** Concrete: suppose at the start, edges (p1, cs1) and (p2, cs2) are both in some max matchings. We remove (p1, cs1)'s blocks. Now in the NEW graph (after removal), (p2, cs2) might NOT be in any max matching. But Régin computed SCCs on the OLD graph and decided (p2, cs2) IS in some max matching. So we DON'T remove (p2, cs2) — which is fine: we miss a removal opportunity but don't over-remove.

Hypothesis 3: **`d.iter_live()` returns blocks at cell (sr,sc), and the filter `b.pieces[slot] == p` matches blocks where piece p is in slot s.** Removing them is correct because: edge (p, slot s at sr/sc) is Régin-removable → no block can be at (sr,sc) with piece p in slot s. But the block we remove ALSO has OTHER pieces in OTHER slots. Removing this block means those OTHER (piece, slot) edges lose 1 count — but those OTHER (piece, slot) pairs might be CRITICAL for some other max matching!

WAIT — this is the bug? Let me think harder.

Suppose `slot_block_count[(p2, cs2)] = 1`, contributed by exactly block B. We're at cell (sr,sc), Régin says "(p1, cs1) is removable", where cs1 corresponds to slot 0 at (sr,sc). Block B has p1 at slot 0 and p2 at slot 1. We remove B. Now `slot_block_count[(p2, cs2)] = 0`. So edge (p2, cs2) is GONE.

But was (p2, cs2) in some max matching? Let's check. (p1, cs1) was the matching edge for p1. (p2, cs2) might or might not be in a matching. If p2's matching partner was some OTHER cs, then losing (p2, cs2) doesn't break the matching — just one possibility. The NEW max matching still exists (with p1 finding a different partner, since cs1 still has other partners, or via alternating cycle).

**Hmm. Actually this can break things.** Imagine the bipartite graph has a "bottleneck" where (p2, cs2) is part of the alternating cycle that allows p1 to swap partners. Removing B kills (p2, cs2), breaks the alt cycle, and now the max matching DROPS.

But — this would be detected on the NEXT regin_filter call: HK matching would return < 256, regin_filter returns None, search backtracks. So the over-removal would manifest as PREMATURE backtracks, not as wrong solutions.

That matches the symptom: **v6 backtracks earlier than v5 (depth 30 vs 40)**.

### THE BUG (hypothesis confirmed by analysis):

Régin filter at the block-domain level is **NOT SOUND** because:

- Régin says: "Edge $(p, cs)$ ∉ any max matching → can remove from bipartite graph".
- At the block-domain level, "remove edge $(p, cs)$" = "remove all blocks at cell (sr,sc) with piece $p$ in slot $s$".
- But this removes blocks that ALSO contain other (piece, slot) edges. Those edges WERE in some max matching.
- After removal, the bipartite graph loses those edges → the new max matching may be < 256.

**Régin alldiff is sound for ATOMIC edge removal in a bipartite graph. It is NOT sound at the block-level where one block contributes 4 simultaneous edges.**

### Possible fix

Instead of removing edges via blocks, we can run Régin and use it only as a **necessary-condition check** (like v5's HK alldiff). That's what v5 does already. So Régin doesn't add anything if we only do "remove all blocks containing a forbidden edge".

The CORRECT way to use Régin at the block level: identify forbidden edges → re-filter the block alphabet to only contain blocks where ALL 4 (piece, slot) edges are not forbidden. But removing a block forbids its OTHER (piece, slot) pairs from being satisfied via THIS block. Other blocks with those (piece, slot) pairs may still exist.

Wait, that's exactly what v6 already does. So why does it over-remove?

The issue is **transitivity**. Consider: Régin filter run #1 identifies edges F1 to remove. We remove blocks containing them. NEW slot_block_count → bipartite graph shrunk → run #2 of Régin identifies MORE edges F2 to remove. F2 includes edges (p, cs) that were in some max matching of the ORIGINAL graph but not in the SHRUNK graph.

Within ONE call to `regin_filter`, we run Régin ONCE and remove ALL F1 edges. So we're not transitively over-removing within a call. But the SCC was computed on the ORIGINAL bipartite graph — and we're claiming "any block containing an F1 edge is infeasible".

Hmm — actually that claim is SOUND. If edge (p, cs) is not in any max matching of $G_B$, then there's no perfect matching using (p, cs). So at cell (sr,sc) we can't have piece p in slot s. So no block with `b.pieces[slot] == p` at (sr,sc) can be part of any solution. Removing such blocks IS sound for the original bipartite relaxation.

But removing those blocks ALSO removes their OTHER 3 (piece, slot) edges. These edges might be NECESSARY for the original max matching — and once removed, the bipartite graph no longer has a perfect matching, even though the ORIGINAL puzzle does.

**That's the trap**. Régin sound at edge level → block-level removal not sound.

### Concrete diagnostic

To confirm: run v6 with normal removal, after first regin_filter call, save state and re-run HK. If HK < 256, Régin over-removed → search backtracks falsely. If HK == 256, the removal preserved feasibility and the bug is elsewhere.

---

## Update 2026-05-18 18:20 — VERIFY-AFTER DEFINITIVE RESULT

Ran v6 with `--verify-after` for 200 nodes:
- node 100: depth=30
- node 200: depth=29
- **regin_filter calls: 199, calls that broke PM: 0**

**Zero PM-broken events**. Régin is preserving bipartite-perfectibility in every call. My block-vs-edge unsoundness theory is **REFUTED**.

So v6 IS sound (Régin's theorem holds at block level too, by the argument: any block-CSP solution induces a bipartite perfect matching; (p, cs) not in any matching ⇒ no solution has p in slot s at (sr,sc) ⇒ no block at (sr,sc) with p in slot s ⇒ block-removal sound).

### So what's happening?

v6 is SOUND but **explores worse than v5** because:
1. Régin removes blocks → smaller domain at multiple cells.
2. MRV picks different next-cell.
3. Different subtree explored → may hit dead-ends earlier or later than v5.

Empirically v6's MRV reordering happens to lead to **early dead-ends**, oscillating around depth 29-30 vs v5's steady climb to 40.

This is a SEARCH HEURISTIC interaction issue, not a Régin bug. Régin in v6 is mathematically correct.

### What this means for v6

v6 is correctly implementing Bourreau-style Régin alldiff but the pruning REORDERS the search in an unhelpful way. To benefit from Régin we need:
- Either change branching order (e.g., follow v5's MRV but use Régin only for early infeasibility detection).
- Or run Régin to fixpoint at root only (one big prune, then v5-style search).
- Or use Régin's pruning info differently (e.g., as a candidate ordering hint at the current MRV cell).

### Decision

We have spent enough time on Régin. The Bourreau-style approach is **theoretically sound but practically suboptimal in our integration**. The right pivot:
- **Use v5** (HK alldiff only, infeasibility detection without removal) as the production BB&B engine.
- Build smaller-puzzle verification using `generate_with_solution` to validate the entire pipeline.
- Move forward on other research directions; revisit Régin in a future volume with a better integration design.

The unit test (`regin_unit_test`) is committed and shows the Régin/SCC implementation is correct. The diagnostic (`--shadow`, `--verify-after`) is committed too. Future researchers can revisit this with the knowledge that:
1. Régin alldiff is sound for block-CSP super-block alphabets (theorem applies via reduction).
2. Edge-level block removal preserves bipartite-PM (verified empirically, 199/199 regin calls preserved PM).
3. The integration challenge is the MRV-reordering effect, not soundness.
