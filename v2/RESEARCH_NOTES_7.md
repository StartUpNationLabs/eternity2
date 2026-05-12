# Eternity II research — volume 7 (sister vol-7, exploration mode)

Continuation in spirit of vols 5 and 6, but with a different mandate.

- **Vol-5** (night, 1782 lines): exhausted soft-penalty PT, NE1/NE2/NE2-iter,
  NE-BP, max-clique RO, Wauters/Salassa polishing, GA-light/cascade.
  Result: 449 → 452 → **453**.
- **Vol-6** (morning, 375 lines): rare-color/skeleton/free-zone analysis,
  EvalMaxSAT *minimal* encoder; **rigorously proved 453 is OPTIMAL for
  inner k=3, 4, 5 given its outer fixed**. Inner-only optimisation
  cannot break 453. Consensus seeding lands back in the 452 basin.
  Hard-skeleton + free-zone backtracking gives only 357 (over-rigid).
- **This vol-7** (May 12 ~08:00 CEST, sister-session): explicit mandate
  is **OUT-OF-FIELD ideas to escape the 453 basin**. Vols 5/6 were
  execution-mode; vol-7 is exploration-mode.

Authoritative state in `memory/project_e2_state.md`. Best score
**453/480** with 27 mismatches.

---

## Mission

Get OUT of the 453 basin (and its 452/451 neighbours). Vols 5-6
ruled out:

- Soft-penalty PT (NE2/NE2.1/NE2-iter) — redistributes, conserves budget.
- Single-T SA / vanilla PT — bounded by moat depth ≥5.
- ALNS at 4×4 / 5×5 destroys — below moat depth.
- ALNS + MWPM (cell-defect) — same.
- Edge-CP + PT — alldiff is the rigidity locus.
- Wauters TA (Hungarian, K=16) / TSR / max-clique RO — PT removes
  the slack their polishing assumes.
- Memetic GA at 4×4 / 6×6 (GA-light / GA-LARGE / GA-CASCADE) — reaches
  452/453 but does not break 453.
- Consensus seeding — collapses back to 452 basin.
- Anti-consensus — wrong target; corner-cascade edges.
- Hard skeleton + free-zone backtracking — over-rigid, 357.
- Frame-first 100-1000 borders — 450 ceiling; never broke 449 by
  border-search alone.
- BP on edge-color — paramagnetic; all rigidity lives in alldiff.
- Survey Propagation — 1.5/5 by literature review (short cycles + no
  rigid phase).
- IsingFormer / GFlowNet / diffusion-CO — 2-4 weeks, no track record.
- GPU/FPGA/quantum SAT — academic theater at 5-clue scale.
- EvalMaxSAT on full WCNF — no `o` lines, alldiff too dense.

What proves 453 is the ceiling for the current outer: vol-6's k=3,4,5
EvalMaxSAT optimality run. To get 454+ we **must change the outer**
— meaning the border, the corners, or the layer 0-1 rings, or the
strain-front configuration around (7,8).

## Working hypotheses for vol-7

1. **The puzzle designer (Lord Monckton) had a specific construction
   recipe** — maybe published, maybe in patents — that pre-determines
   which abundant-color pairs are "decoy" pairs intentionally placed
   to create combinatorial near-degeneracy. If so, reverse-engineering
   the construction would give a strong informed prior.
2. **The community (eternity2 groups.io, hobbyist solvers since 2010)
   may have observations we haven't seen** — folklore that didn't make
   it into peer-reviewed lit but that points at structural levers.
3. **Adjacent problems** (Potts-model defect dynamics, genome assembly
   overlap-layout-consensus, jigsaw-2024-2026 vision, origami flat-
   foldability, gauge fields on lattices) may bring techniques that
   nobody has tried on E2 specifically.
4. **Vols 5-6 left implications unexplored.** Specifically:
    - The **32-cell free zone** (0.80 threshold) is a *description*
      but the over-rigid backtracking failed because skeleton was held
      fixed. What about *soft* skeleton + *joint* search?
    - The asymmetric (7,8) hint creates the south-central strain
      cascade — but we never tested **what happens if we *manufacture*
      a hint-set with different asymmetry** to identify which exact
      mechanism is at fault.
    - The **bucas-overlap-19% between two 450 basins** says there
      are *very* different basins out there. We may not have sampled
      enough basins to find a 454-class outer.

## Why this vol matters

This is sister-vol-7; vol-6 is still alive in another session (tail
of /tmp/ga_xl.log). No CPU contention because GA-XL already finished
its compute and the listener is idle. Vol-7 has the full machine and
the obligation to think differently rather than rerun.

Score is 453/480; any move that yields 454+ is the headline.

## Operating rules (vol-7)

- Spawn research agents liberally for parallel literature mining.
- Commit after every significant finding.
- Update auto-memory when something session-defining happens.
- Cite sources when forum/agent claims something — link, archive.
- Negative results matter; clean "X but Y" entries are valuable.
- The cron loop at 11,56 \* \* \* \* will ping with reflective prompts;
  honour it (~45 min cadence).

## Per-experiment format

```
### <name> — <timestamp>
**Hypothesis**: …
**Setup**: …
**Result**: …
**Verdict**: …
```

## Vol-7 dispatch log

### 08:00 CEST — session start, parallel agents queued

Three research agents dispatched in parallel (M1 = Monckton, F1 =
forum/community, X1 = 22-color Potts/lattice defects). Each scoped
to 600-900 words, background, so vol-7's main thread can synthesise
while they run.

While they run, vol-7 main will:

1. Re-skim vol-5's bottom half (~lines 1200-1782) for any
   pattern that didn't surface from the synthesis — done.
2. Read NIGHT5_NEXT_DAY for the morning-Claude playbook — done.
3. Choose 1-2 cross-domain angles X1/M1/F1 surface for deeper work.
4. Begin building an outer-configuration search that uses the
   inner-optimality oracle (vol-6's k≤5 EvalMaxSAT) — this is the
   one genuinely new algorithmic class implied by vol-6 but not yet
   built: enumerate small perturbations of the 453's outer, solve
   each one's inner via MaxSAT to optimum, pick the best.
