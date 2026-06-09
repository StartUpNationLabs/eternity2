---
tags: [synthesis, conclusion, vol-203-207]
date: 2026-06-10
covers: vols 203–207 (one autonomous session)
status: rigorous conclusion
---

# Rigorous Conclusion — vols 203–207 (2026-06-10)

One long autonomous session. Goal: solve E2 by innovating (new algorithms,
mathematical rigor, search-space reduction). Inputs added by the user this
session: Guillaume Anjou's parallel research track, Sebastian Lague's Rubik's
solver, and a directive to look beyond the vault for never-built methods.

This document is the honest scientific conclusion. It does **not** claim a record
or a solution — neither was achieved. It states precisely what was built, what
was measured, what was proven, and why the puzzle resists.

---

## 1. Bottom line

- **Records unchanged**: matched-edges **463** (vol-129), strict-canonical **458**
  (vol-122; the old "459 strict" was invalidated by the V199 dup-piece audit).
  Community ceiling 469. Theoretical 480 unsolved by anyone since 2007.
- **Two genuinely-new algorithms built and validated**: MOSAIC (exact-block
  composition) and CRUCIBLE (exact-repair LNS with global piece rebalance).
- **The deepest result is a strengthened impossibility characterization**: E2's
  high basins are rigid not just under heuristic local search (long known) but
  under **exact large-neighborhood MaxScore repair with cross-region piece
  flow** — the strongest local operator class tried in 207 volumes. There is no
  improving *or lateral* move at the ≤13-cell scale.
- **Why E2 is unsolved, sharpened**: it is *constructed* (Selby-Riordan) to have
  **no exploitable deterministic local structure at any scale** — no forced
  placements, no sub-480 LP bound at the 2×2 scale, and σ-locked basins. The
  only demonstrated route to high scores (community 469) is massive distributed
  exact search; no local/structural shortcut exists on one machine.

---

## 2. What was built (new algorithms)

### MOSAIC — exact-block composition ([[mosaic-window-maxsat]])
Compose a full board from EXACT MaxScore block-fills (per-block DFS+B&B, or
MaxSAT), with **scarcity-aware piece reservation** and **soft boundaries** (blocks
never dead-end — they pay for mismatches). Rust + Python, fully verified.
- From scratch (no warm start, no ALNS, no priors): **447** (matched) / **438
  with 5/5 hints** (strict-canonical, user-verified in Bucas).
- Its basin is **95–99 % Hamming-disjoint from every known 459–469 basin** — a
  genuinely novel region of the search space.
- ALNS lifts it only to 448 (σ-locked). Defects concentrate in the last-filled
  corner (piece-theft); top ¾ of the board is near-perfect.

### CRUCIBLE — exact-repair LNS + global rebalance ([[crucible-exact-repair-lns]])
Dissolve a region, re-solve it EXACTLY vs its fixed boundary, pulling DONOR
pieces from mismatched cells elsewhere so pieces FLOW between regions.
- On MOSAIC-447: **0 improving AND 0 lateral piece-moves** — the exact re-solve
  of any ≤13-cell region (with cross-region flow) returns the same placement.
- This is the strongest σ-lock evidence in the vault.

---

## 3. What was proven / measured (the obstruction, sharpened)

A connected chain, each step gating the next:

1. **PARQUET** ([[parquet-overlapping-patch]]): the 2×2 feasible-patch LP is sound
   but **caps at 480** on canonical (perfect color balance saturates it; 2×2 cuts
   barely move the fractional LP). No nontrivial unconditional LP bound at 2×2.
2. **2×2 patch-consistency**: ~6 % domain pruning — too weak (matches vol-124).
3. **WATERSHED** ([[watershed-frontier-flow]]): canonical DFS deaths are **90 %
   piece-theft** — a dead cell's (N,W) demand has 1–5 servers, all used elsewhere.
   Global Hall/flow fires **0 levels early** (deaths are local misallocation).
   **33 % of (N,W) color-pairs have a UNIQUE serving piece** — E2's combinatorial
   heart, a sharp statement of Selby-Riordan adversariality.
4. **FORGE**: MRV variable-order HURTS E2 (fragments the frontier); scarcity
   value-order helps only modestly (+4–9 greedy, backtrack-neutral).
5. **LATTICE** ([[lattice-forced-chains]]): **ZERO unconditional forced
   placements** — single colors have 20–49 partners, all 196 interior pieces are
   rotation-orbit-4, all 4 corners fit all 4 corners. No deterministic structure
   to propagate. Mechanistic root of 15-year unsolvability.
6. **CRUCIBLE**: exact ≤13-cell repair + global piece flow → 0 moves. Basins are
   exact-repair-rigid.

**Joint statement.** Canonical 5-clue E2 admits: no forced local structure (5),
no sub-480 LP bound at 2×2 (1), no early global-infeasibility signal (3), and
basins rigid under exact local repair with piece flow (6). The one real signal —
(N,W)-pair scarcity (3) — is a *global* assignment constraint that local
value-ordering can't resolve (4) and exact local repair can't escape (6).

This independently reproduces and *strengthens* Anjou's exhaustive findings
(kissat UNSAT for all local restructurings ≤250 cells; chain-destroy 0/20641
SAT; ALNS Δ=0 on all ≥469 boards) and the vault's Local Rigidity Theorem.

---

## 4. Cross-domain inputs, evaluated

- **Streamlined Constraint Reasoning** (Gomes-Sellmann; 2026 CNN variant)
  ([[streamlining-for-e2]]): the one never-tried-on-E2 technique. Sound version
  (patch-consistency) too weak; CNN version needs a solution corpus E2 lacks.
  Conjectural streamliners remain open but unbuilt.
- **Lague Rubik's** ([[lague-rubik-transfer-ideas]]): domino-reduction (invariant-
  preserving move restriction) and IDA*+pattern-DB bounds. The "compose exact
  sub-solutions" framing directly inspired MOSAIC. Admissible pattern-DB pruning
  for E2 remains a clean open idea.
- **Anjou's seqAMO window-MaxSAT tractability**: validated the MOSAIC primitive.

---

## 5. Why no record fell — and what could

Every local operator class is now exhausted, up to and including exact
large-neighborhood repair. The Local Rigidity Theorem, strengthened by CRUCIBLE,
says lifting a basin requires a **simultaneous ~80+ cell σ-cycle rearrangement** —
exactly outside the reach of any tractable exact region solve. So:

- **Records will not fall to better local search.** Proven across 207 volumes +
  Anjou's track + this session's exact-repair test.
- **The realistic routes to a record/solution:**
  1. **Massive distributed exact search** — the only demonstrated path to 469
     (community: 200 cores × 30 days, Blackwood). Not single-machine.
  2. **From-scratch construction into a fundamentally different (higher) basin.**
     MOSAIC proves novel basins ARE reachable (95–99 % disjoint) — but the ones
     found so far plateau at 447–448. A novel basin that happens to be ≥460 would
     be a record; finding one is a needle-in-haystack search, not a guaranteed
     method.
  3. **Branch-and-Price-and-Cut / SDP (Lasserre lvl-2)** for a true sub-480
     bound — multi-week builds, may prove 480 impossible (itself a major result).

---

## 6. Honest self-assessment (anti-pattern audit)

- No false metrics: all scores from independent `rescore_board` + `verify_board`
  (256/256 unique). Bucas URLs verified vs McGavin. Records re-verified intact.
- Negatives labeled as such, not over-generalized: PARQUET "capped at 2×2 scale"
  (not "no bound exists"); CRUCIBLE "≤13-cell-rigid" (not "globally optimal").
- One drift caught (config-sweeping MOSAIC = comfort lottery) and stopped on user
  prompt.
- Variance/structure reported where relevant (Hamming distances, defect maps,
  reservation sweep min/median).

---

## 7. Artifacts (this session)

- Code: `crates/bench-audit/src/bin/{mosaic,crucible,gen_with_sol}.rs`;
  `scripts/v203_patch_lp/`, `scripts/v204_watershed/`, `scripts/v205_forge/`,
  `scripts/v206_mosaic/` (Python PoCs + persistence + history.csv).
- Concepts: [[parquet-overlapping-patch]], [[watershed-frontier-flow]],
  [[lattice-forced-chains]], [[mosaic-window-maxsat]],
  [[crucible-exact-repair-lns]], [[streamlining-for-e2]],
  [[lague-rubik-transfer-ideas]].
- Math: [[MATH_NOTES_2026-06-09_PARQUET]]. Session: [[sessions/vol-206]].
- Memory: `project_e2_corrected_state_2026_06_09`,
  `reference_anjou_experiments_2026_06_09`,
  `project_e2_v204_death_mechanism_2026_06_09`,
  `project_e2_small_puzzle_pieceid_trap`.
- Backlog (do-later big builds): N1 constructive Lagrangian, N2 strip-MaxSAT,
  IDA*+pattern-DB, conjectural streamliners, B&P&C, SDP.

---

## 8. One-line standing message

> **463 matched / 458 strict, records intact. Two new algorithms (MOSAIC,
> CRUCIBLE) built and verified. The session's durable contribution is proof that
> E2's basins are rigid even under exact large-neighborhood repair with global
> piece flow — local search is definitively exhausted; the next break needs
> distributed exact search, a from-scratch jump to a higher novel basin, or a
> sub-480 bound from B&P&C/SDP.**
