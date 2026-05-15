# Current vol — vol-59 CLOSED, vol-60 queued — 2026-05-15

**Session 2026-05-15 fully closed**. 6 vols shipped (54, 55, 56, 57,
58, 59) across ~3 hours of autonomous compute.

## Standing record state

- **458** matched edges, vol-32 vanilla_fast + ALNS (3/5 canonical hints).
- ULTRA-CONFIRMED locally MIP-optimal across 22 cluster geometries
  spanning 3 basin families (family A, family B, McGavin 469).
- Matches Schaus & Deville 2008 academic CP+VLNS SOTA.
- Empirical record-break probability in vanilla pipeline: ≤ 0.6%.

## Vol-60 candidates

After vol-59 T4's theoretical finding that E2's flat cause-graph
limits SAT-style 1-UIP, the CDCL direction is uncertain.

1. **Different basin source** — McGavin pipeline replication
   (multi-week multi-machine).
2. **Schedule-relaxation** in CP search (multi-day, vol-15 tried, hit
   depth-wall 80; might revisit with different relaxation schedules).
3. **RL self-play value order** (vol-30 BACKLOG, multi-week).
4. **CDCL with E2-specific clause representation** (vol-60 reframed,
   investigate compact per-cell forbidden sets + subsumption).
5. **Cross-puzzle transfer learning** — train on small E2-style
   puzzles, transfer to canonical (vol-28 refuted naive transfer, but
   distribution-matched training was promising).

None are guaranteed wins. The session's most honest conclusion: we've
reached the academic ceiling for CP+VLNS approaches. Breaking 458
requires either substantially more compute or a paradigm shift.

## Linked

- [[../sessions/SESSION_2026-05-15_summary]] — full session writeup
- [[../sessions/vol-59]] — most recent vol
- [[../concepts/standing-458-record-status]] — comprehensive status
