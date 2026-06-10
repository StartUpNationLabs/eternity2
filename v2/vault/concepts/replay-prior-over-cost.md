---
name: replay-prior-over-cost
description: "REPLAY mode (vol-213): priors-buffer candidate ordering by (Reverse(weight), cost) across ALL break segments, plus the double-break operator (cost-2 segments). Makes witness boards exactly walkable by the break-DFS; discovered that community strict-460s contain 4-5 double-break cells and are structurally unreachable for violate-≤1 engines."
status: built
metadata:
  type: concept
---

# REPLAY mode (prior-over-cost) + the double-break operator

**Origin**: vol-213 (2026-06-10), day 2. **Files**: `crates/cloister/src/dfs.rs`
(priors fill + `Seg.violate: [u8;2]` + `max_cell_breaks`), bin flags
`--prior-over-cost`, `--max-cell-breaks`.

## Definition

Two coupled mechanisms in the CLOISTER-II break-DFS:

1. **Prior-over-cost (REPLAY)**: with priors active and `break_open`, the
   per-depth candidate buffer drains ALL open segments (not just cost-0)
   and sorts by $(\text{Reverse(weight)}, \text{cost})$. A weight-1
   break candidate (a piece the witness pool places at this cell)
   outranks every unseen cost-0 candidate, so a witness walk pays its
   breaks AT the witness's break cells instead of detouring into cost-0
   subtrees. Sound because `break_open` is invariant within a cell
   instance (any backtrack through depth $d$ resets its cursor).
2. **Double-break (cost-2 segments)**: for each cell with $k \ge 2$
   constraints, $\binom{k}{2}$ segments violating exactly two
   constraints, exposed when `max_cell_breaks ≥ 2`, gated as TWO break
   spends: $\text{spent}+2+\text{hint\_after} \le \text{budget}$ and
   $d \ge \text{sched}[\text{spent}+1]$ (sorted schedule ⇒ implies the
   $\text{spent}{+}1$ gate). Cheap-first segment order [cost-0, cost-1,
   cost-2]; the runtime exposes a prefix.

## ★★ The double-break discovery (vol-213)

`--schedule-from-board` on the community strict-460s emits their break
depths; **duplicated depths = one cell paying 2 mismatches at
placement**. Witness A: 5 doubles (171, 177, 184, 190, 195); witness B:
4 doubles (171, 177, 190, 195). None are hint cells. The pre-vol-213
candidate machinery generated violate-EXACTLY-ONE candidates only ⇒ the
community strict-460s were **unreachable boards for our break-DFS under
any budget/gates/priors/scan**. This bounded the witness-guided track at
455-457 and is a candidate explanation (untested at vol-213 open) for
part of the unguided 450 plateau.

## What we measured (vol-213, strict460a/b frames, 8 seeds × 300 s, et14, hinted)

| config | result |
|---|---|
| REPLAY mcb=1, witness A | **458/458/458 — all 8 seeds the IDENTICAL board** (II 352 + IB 46 + BB 60, 22 breaks, 5/5 hints, independently rescored). Diff vs witness: 14 cells, ALL in rows 12-13, first divergence = pos 212 = the depth-171 double-break cell. Replay walked the witness perfectly to its first double-break, then re-solved the tail within violate-≤1: II +2, IB −4 ⇒ −2 total. |
| REPLAY mcb=1, witness B | 456 ×8 (5/5) — forks at B's 171 double (the 167 single replays). |
| REPLAY mcb=2 | see [[vol-213]] — the exact-replay + neighborhood run. |

The mcb=1 result ties the all-time strict record 458 (provenance:
witness-derived, community-460-adjacent basin — distinct from the
vol-122 ALNS 458 basin).

## What's still open

- Unguided double-break: does mcb=2 lift the 450 plateau without
  witness priors, or flood the anytime-min? (A/B queued.)
- Triple-break cells: do any high community boards pay 3 at one cell?
  (Check more witnesses' schedule-from-board duplicates.)
- PREFIX VAULT interaction: bank mcb=2 perfect prefixes ≥160.

## Linked

[[cloister-ii-border-anchored]], [[vol-213]], [[vol-212]]
