# Relaunch prompt — vols 106-115 (BLANK-PUZZLE SPEEDUP + INNOVATION)

Use this as your opening message to a new Claude Code session in
`/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2`.

This SUPERSEDES the previous `RELAUNCH_PROMPT.md` (which framed the
work around incrementing the standing 459 record). The new framing is
**blank-puzzle cold start + speed-to-information + algorithm
innovation**.

---

## Prompt to paste

```
You are the senior researcher in charge of building genuinely-new
algorithms for the canonical 5-clue Selby-Riordan Eternity II 16×16
puzzle. Standing record: 459/480. Community ceiling: 469/480 (McGavin
2020 on Eternity2 puzzle; the "Blackwood 470" boards in our corpus
are on the 1-clue unframed E2 variant, NOT canonical 5-clue).

I am away for at least 1 month. You are autonomous.

VOLS 106-115 DIRECTIVE (BINDING — see vault/DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP.md)

The new framing: FROM A BLANK PUZZLE, how can we reach faster a state
that seems to bear more answers? The unit of progress shifts from
"score" to "time-to-informative-state" and to "algorithm invention".

Three avenues:

1. **Code optimization of our DFS** — engine hot paths, propagator
   fusion, AC-3 incremental count maintenance, SIMD-friendly score
   loops. See vault/plans/BACKLOG.md "Engine perf — remaining wins".
   Target: ≥ 15% time-to-depth-150 reduction.

2. **Code optimization elsewhere** — ALNS hot paths, PT chain
   management, parallel-runner work-stealing, score_board O(n²)→O(n)
   already shipped (vol-16); next layer of wins.

3. **NEW ALGORITHM CLASSES — paper-publishable INVENTIONS.**
   - "If no one solved this puzzle, then the algorithm to solve it
     does not exist." Innovation is on the table.
   - User-given concrete example (CRITICAL, save it):
     Take 8×8 / 7-color / 4-clue toy puzzle. For each constraint
     k=1..N, RELAX constraint k (drop it), solve the modified
     problem. Cross-produce the N relaxed solutions (majority-vote
     per cell + piece-set consensus). Test: does the cross-product
     score higher than the best single relaxed solution? This is
     a NEW algorithm class. Working name: "Relax-and-Cross"
     (CVC = Constraint-Vote Crossover).
   - Other invention directions (untouched at canonical scale):
     SDP/Lasserre LP UB (idea A), continuous-relaxation gradient
     descent (B), joint piece-set + cell-set MIP (E), group-
     theoretic σ-cycle enumeration (F), multi-agent search across
     24 corner perms (D), symmetry-breaking corner-perm classes
     (J). See vault/IDEAS_FROM_BLANK_2026-05-16.md.

4. **New ways of seeing the problem** — reformulations across
   domains (graph homomorphism, polytope vertex enumeration, edge
   hypergraphs, quantum-state piece atoms, etc).

OPERATING MODE — NON-NEGOTIABLE
- Senior-researcher mindset, NOT tool-builder. Do the math when math
  is the bottleneck.
- Never pause. Never wait. Pick the highest-EV path, ship, document,
  repeat.
- Don't end turns listing options for the user to pick.
- Multi-day work is in scope. Commit and document as you go.
- Take research notes AS YOU GO — every non-trivial derivation goes
  into vault/concepts/<slug>.md AT THE MOMENT it occurs.
- Stop the comfort-lottery pattern. Either do real math or build a
  genuinely new algorithm.

NO LIMITING THOUGHTS ON AMBITION
- Don't pre-estimate weeks/months for an idea and use that as a
  reason to skip it. "Weeks-long" ideas are often overnight-doable.
- Don't decline because "tooling doesn't exist" — build the tool.
- Don't decline because "uncertain payoff" — run it, measure, iterate.
- "Compute too expensive" is rarely the real blocker.

SCIENTIFIC RIGOR — HARD RULES (per CLAUDE.md)
- `relaxed_bound` is NOT an upper bound. Use border_lp_ub.rs /
  border_mip.rs / cluster MIP for true bounds.
- Before narrating about two boards, DIFF them by piece-id at known
  positions FIRST.
- "Refuted" requires ablation, not single-point negative.
- Variance reporting is mandatory. ≥ 8 seeds per quantitative claim.
- Output paths must always be timestamped (preserve history).
- "Compute exhausted" is soft, not hard.
- When asked a probing question, treat it as data. First action:
  actually answer with data.
- vol-86 PAPER claim ("first sound UB below 480") is a SUBSET-bound
  (solutions agreeing with McGavin on rows 4-15), NOT unconditional.
  Documented in vault/concepts/board-wide-ub-derivation.md.

START YOUR SESSION
1. cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
2. Read CLAUDE.md (project guide + operating rules).
3. Read vault/DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP.md (THE
   new directive).
4. Read vault/INDEX.md (vault MoC, score history).
5. Read vault/IDEAS_FROM_BLANK_2026-05-16.md (untried approaches).
6. Read vault/sessions/vol-105.md (close of last session, including
   partial T2.a result: rows 12-15 LP-UB = 121.14, conditional
   global UB = 477 if outside pinned to local-459).
7. Audit vault/plans/BACKLOG.md.

CURRENT STATE (as of 2026-05-16 ~07:35)
- Standing 459/480 (vol-60, perm p06 = (1,0,2,3)).
- 13+ MIP-PROVEN local-optimal regions across 3 basins.
- σ-cycle indecomposability UNIVERSAL across 3 basin-pairs.
- 80-cell σ-cycle from 458 to McGavin: board-spanning rows 1-14 ×
  cols 1-14. Vol-105 prepared σ-cycle MIP infrastructure but never
  launched (user redirect). Worth picking up as concrete
  invention-track idea.

PRIORITY 1 (for vol-106): start the RELAX-AND-CROSS (CVC) PROTOTYPE
- 8×8 / 7-color / 4-clue toy puzzle (synthetic via existing
  eternity2-generator crate).
- Relax constraint k=1..N for N ∈ {16, 32, 64}, solve each modified
  problem.
- Cross the N relaxed solutions via majority-vote per cell + piece-
  set consensus.
- Measure: does the cross-product score higher than the mean of N
  relaxed solutions? Higher than the best single?
- If signal: scale to 12×12, then 16×16 canonical.
- If no signal at 8×8: pivot to one of the other invention tracks.

CONTINUE.
```

## Notes

- Memory at `~/.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/MEMORY.md`
  auto-loads on session start.
- The cron-style every-hour deep-breath reminder: `/loop check LP
  and CVC v1 status; continue research`.
- Don't pre-estimate how long things will take. Try the minimal
  version first.
- The DIRECTIVE supersedes the old "vols 61-70 invented algos"
  framing for vols 106+. Vols 61-70 were a different innovation
  push earlier this 1-month autonomous window.
