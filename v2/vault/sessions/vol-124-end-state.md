---
name: vol-124-end-state
description: "Vol-124 close (2026-05-17): honest accounting. We did not produce a 480 board this session. The 1h kissat returned UNKNOWN. 2×2 super-block alphabet (127.6M blocks) is too large for direct AC-3 in Python. Path forward is multi-day Rust builds for tasks #70 (MCTS-CnC) and #74 (learned-potential min-cost flow). Stop-hook feedback acknowledged."
metadata:
  type: session
---

# Vol-124 — honest end-state

## What the contract required

Produce a 480/480 matched-edges board on canonical 16×16 Selby-Riordan
Eternity II with 5 hints obeyed.

## What was actually produced this session

**No 480 board.** Standing records unchanged:
- 459/480 (4/5-hint matched-edges) — community-leaderboard convention
- 458/480 (5/5-hint strict-canonical) — vol-122 record break

## What was learned (worth saving)

### Tool-level (durable infrastructure)

1. **W-SAT encoder validated end-to-end** ([[w11-sat-correctness-validated]]).
   Round-trip on 5 puzzle sizes; sabotage tests detect UNSAT correctly;
   single-rotation sabotage flips SAT→UNSAT.

2. **W11 SAT-screen-per-border retired as primary engine**
   ([[w11-border-screen-unviable]]). Border space ~10^7–10^9; per-border
   SAT ~2s → 22 single-thread years for full enumeration. W11 remains
   a useful **verification** tool (post-hoc yes/no in <2s).

3. **W14 super-block alphabet enumerated.** 127.6M internally-matched
   2×2 blocks across 64 super-cells (with 5 hint-pinned super-cells at
   ~5k blocks each, corners at 1.3k, edges at 73k, interior at 4M).
   Foundation built; Python AC-3 propagation OOM's at this scale. A Rust
   port is needed.

### Negative results (so we don't redo them)

1. **W11 corner-perm sweep**: 240/240 UNSAT across 24 corner-perms × 10
   chain-solutions per side. The right 480 border is not in this class.

2. **1h kissat on full canonical SAT encoding**: returned `s UNKNOWN`
   after 3,587 seconds. CDCL alone cannot decide canonical E2 in
   single-thread reasonable time.

3. **W3 Vandermonde-LP (Kovalsky-Glasner 2014)**: authors §5.2.3 explicitly
   say their method failed on E2. Task #59 deleted.

4. **W15 QUBO on full canonical**: 156,816 binary variables. Fits only
   Fixstars Premium tier ($2k/mo). 4×4 generated puzzle test was
   contaminated by BORDER=0 color collision (canonical uses BORDER=0
   as dedicated outside-color, no collision). 3×3 puzzle SOLVED PERFECTLY
   via neal SA → formulation is correct in principle, but local
   simulated annealing won't scale to 157k vars in any reasonable budget.

5. **"Symmetry-break corners"**: retracted by user. Canonical E2 is
   maximally asymmetric (vol-27, vol-65). Memory
   [[feedback_e2_no_textbook_symmetry_breaking]] saved.

### Strategic lessons

1. **Multi-week projects are now sanctioned** (user explicit, memory
   [[feedback_multi_week_projects_allowed]]). The remaining viable
   attacks (MCTS cube-and-conquer, learned-potential flow,
   AlphaMapleSAT-style SAT) all need multi-day Rust implementations.

2. **The 2×2 super-block idea (Bourreau 2020) requires Rust.**
   Python at 127.6M blocks OOMs during AC-3 indexing. A direct port
   to `crates/sat-encoder` is the right move — it's already validated
   on the 1×1 encoding.

## The actually-tractable path forward

The 4 remaining pending tasks span 3 axes:

### Axis A: SAT solver enhancements
- **Task #70 W13 — AlphaMapleSAT MCTS cube-and-conquer**.
  Multi-week Rust build, but ~1.6–7.6× speedup demonstrated on related
  Ramsey/Kochen-Specker problems. Best fit for our current 156k-var
  SAT encoding which kissat alone times out on.

### Axis B: Smarter encodings
- **Task #71 W14 — 2×2 super-block SAT**. Needs the W14 alphabet
  (built) ported to Rust with AC-3 propagation. After AC-3, the
  pruned super-cell CSP can be encoded into the existing `sat-encoder`
  and fed to kissat. Multi-day.

### Axis C: ML-guided exact algorithms
- **Task #74 W17 — Learned-potential min-cost flow** (KnotFold-style).
  Train per-(piece, cell) potentials from the ~150 459-basin corpus.
  Solve flow optimization. Different from SA/CDCL — uses corpus
  data the others can't. Multi-week.

## Recommendation for next session

The HIGHEST EV next action: **port W14 super-block alphabet to Rust**.
Reasons:
- Builds on validated SAT infrastructure (`crates/sat-encoder`).
- The Python AC-3 OOM is solely an implementation issue; Rust with
  bitset-indexed sets will handle 127M blocks in 2-4 GB RAM.
- After AC-3 pruning, the super-cell SAT encoding is dramatically
  smaller than the 156k-var 1×1 one — fits within kissat's tractable
  range.
- If even this fails, the conclusion (canonical E2 not solvable by
  current CDCL + super-block) is paper-publishable.

Estimated scope: 3–7 days of focused Rust work. User has explicitly
sanctioned multi-week projects.

## Stop-hook feedback acknowledged

The hook is correct: the contract was not met this session. The
artifacts produced are tools and plans, not a 480 board. The honest
next step is multi-day implementation, not more lateral exploration.
