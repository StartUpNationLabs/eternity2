# Current vol — vol-62 (2026-05-15)

**Standing record**: 459/480 (cross-machine SOTA + local tie, vol-60).
**Directive**: Vols 61-70 must each be a genuinely-new invented algo
([[../plans/VOLS-62-70-ROADMAP.md]]).
**Vol-61 status**: in-flight (faithful SOTA replay; stage 3 = 8 ALNS
basic 30min seeds incl seed=42 to attempt 460+).

## Binding items (≤ 3)

### T1 — Vol-62 algorithm: cluster-defect destroy (BUILT, AB pending)

Done so far:
- β₁ measurement on 2,293 saved boards refutes Homotopy-ALNS (β₁ = 0
  on all records ≥ 458). Concept marked `refuted` with full evidence.
  See [[../concepts/homotopy-alns#refutation]].
- New op `ComponentClusterDestroy { cluster_radius, halo }` shipped
  in `crates/localsearch/src/alns.rs`. Exposed via `--ops cluster_only`
  and `--ops winning5_cluster` in alns_only.
- AB test script ready: `scripts/vol62_cqd_smallcomp_ab.sh` — 3 ops
  arms × 5 seeds × 5min on local 459 board.

Pending: AB test launch (waiting for vol-61 stage 3 to free cores).

### T2 — vol-62 close

Write `sessions/vol-62.md` after AB results. Update BACKLOG. Pivot to
vol-63 (Backbone-Adversarial-Repair) ONLY after auditing codebase
up-front for already-implemented variants (vol-62 lesson learned: did
NOT audit before writing concept; ComponentDestroy already existed,
forced honest correction).

## Audit-at-open compliance

This vol opened informally during compaction; full audit deferred to
vol-62 close. Aged unbuilt items in BACKLOG.md to revisit at close.

## Linked

- [[../concepts/homotopy-alns]] (refuted)
- [[../concepts/component-quotient-destroy]] (partial — measurement
  + op shipped, AB pending)
- [[../sessions/vol-62]]
- [[../plans/VOLS-62-70-ROADMAP.md]]
