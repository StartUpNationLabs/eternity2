---
name: ladder-prefix-racing
description: "LADDER (vol-214): successive-halving prefix racing — many cheap single-epoch probes bank their deepest prefixes; top-k deep AND mutually-diverse prefixes get pinned (--init-prefix) and promoted through budget rungs (5 s → 30 s → 300 s) with exact endgames. User idea + Verhaard progress-aborts (--abort-below) + diversity dedup. Engine: forced_prefix in DfsParams; backtracking through the pin cascades to epoch restart."
status: built
metadata:
  type: concept
---

# LADDER — successive-halving prefix racing

**Origin**: vol-214 (2026-06-10/11), from the user's racing proposal
("hundreds of 5 s starts, promote the deepest"), composed with
Verhaard's progress-restart rule (~5× claim) and vol-213's banked-
prefix insight (perfect-171 prefixes exist but are measure-tiny in
shuffle space — concentration beats lottery).

**Files**: `crates/cloister/src/dfs.rs` (`abort_below`,
`forced_prefix`), `cloister2` flags `--abort-below D:N`,
`--save-prefix`, `--init-prefix file:K`,
`scripts/v214_ladder/{ladder.sh, ladder_rank.py}`.

## Definition

1. **Rung 1 — probes**: N single-epoch 5 s runs (distinct seeds),
   perfect walk (no gates), `--abort-below` kills sub-envelope epochs;
   each banks its deepest prefix as a sparse board JSON.
2. **Rank + diversify**: sort by depth; greedily keep prefixes with
   ≤ 80% piece-placement overlap against all kept ones (σ-basin
   funneling is the known failure mode of naive go-with-the-winners).
3. **Rung 2**: top-12, pinned at depth−15 (`forced_prefix` = forced
   cells without hint reservation/req; backtracking through the pin
   cascades to epoch restart via the forced-unwind), 30 s × 4 seeds,
   et14 + gates spread (K+2, 182].
4. **Rung 3**: top-3 by rung-2 best total, 300 s × 8 seeds.

Promotion score v1 = banked depth, then rung-2 totals. v2 candidates:
depth − λ·LEDGER-deficit (deficit as prefix-quality), per-prefix choke
gates.

## Theory

This is successive halving (Hyperband's inner loop) / Aldous-Vazirani
go-with-the-winners adapted to anytime break-DFS. It exploits the
measured heavy-tail of epoch walls (70-151 across restarts) and the
fact that deep perfect prefixes are reusable capital, while fixed-
interval restarts discard them. Verhaard's restart criteria are the
1-rung special case.

## Measurements

**Run 1 (2026-06-10 night, strict460a bordered+hinted, ~25 min total):**
- Rung 1: 104 × 5 s probes → 104 banked prefixes, depths 125-151
  (median 140) — the heavy tail is real (d151 found in 5 s).
- Rung 3 (top-3 at 300 s × 8): d146-prefix → **450/451/451, all 5/5,
  rescored 451/480** (II 342 + IB 49 + BB 60); d151 → 448/449/450;
  d148 → ~447/449.
- **FIRST ESCAPE from the universal 444-450 band** (55 frames, every
  recipe): +1 over the vol-212 plateau (which needed 2 h budgets), +3
  over the same-budget hinted control (446/447/448), robust across
  seeds (median = max). Provenance: no witness interior guidance; the
  frame is the witness ring (strict460a).

Open: scale N; recursive ladders (probe beyond a pinned prefix → bank
deeper prefixes → re-pin); LEDGER-deficit promotion scoring;
per-prefix choke gates; multi-frame ladders via [[framegen-chain-feasibility]].

## Linked

[[replay-prior-over-cost]], [[ledger-color-deficit]],
[[cloister-ii-border-anchored]], [[scan-order]], session [[vol-213]]
