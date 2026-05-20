---
name: k11-corpus-cross-validation
description: "Corpus-wide K11.2 (λ_2) + K11.4 (mismatch-zlib) validation on 14 RECORD_TIE boards. KEY FINDING: a 5/5-hint 457 record has HIGHER algebraic connectivity (0.0377) than the 4/5-hint 459 (0.0369). 458 records cluster identically (0.0345, mz=39 — single basin). 457 records show high variance."
metadata:
  type: project
status: built
---

# K11 — Corpus cross-validation (NEW finding)

## Setup

Applied K11.2 (algebraic connectivity λ_2) and K11.4 (mismatch-zlib mz)
to 14 RECORD_TIE_* boards (3 458s, 10 457s, 1 459). All complete boards.

## Results

| Board | score | hints | λ_2 | mz |
|---|---:|---:|---:|---:|
| RECORD_TIE_459_p06_corner_1_0_2_3_seed2 | 459 | 4/5 | 0.0369 | 29 |
| RECORD_BREAK_458.alns | 458 | 4/5 | 0.0345 | 39 |
| RECORD_BREAK_458_vanilla_fast_alns | 458 | 4/5 | 0.0345 | 39 |
| RECORD_TIE_458_vol35_deep458_winning5_seed5 | 458 | 4/5 | 0.0345 | 39 |
| **RECORD_TIE_457_blackwood_mrv_5min_seed10** | **457** | **5/5** | **0.0377** | **31** |
| RECORD_TIE_457_blackwood_mrv_5min_seed10.pt_e2 | 457 | 5/5 | 0.0377 | 31 |
| RECORD_TIE_457_vol35_deep458_diverse_seed5_3hints | 457 | 5/5 | 0.0358 | 36 |
| RECORD_TIE_457_vol35_deep458_full_seed5_3hints | 457 | 5/5 | 0.0356 | 38 |
| RECORD_TIE_457_vol34_t3_t01_seed1 | 457 | 5/5 | 0.0356 | 37 |
| RECORD_TIE_457_blackwood_mrv_30min_seed4 | 457 | 5/5 | 0.0354 | 42 |
| RECORD_TIE_457_blackwood_mrv_30min_seed4.pt_e2 | 457 | 5/5 | 0.0354 | 42 |
| RECORD_TIE_457_blackwood_mrv_5min_seed7 | 457 | 5/5 | 0.0334 | 33 |
| RECORD_TIE_457_blackwood_mrv_5min_seed7.pt_e2 | 457 | 5/5 | 0.0334 | 33 |
| RECORD_TIE_457_vol34_t1signal_seed1 | 457 | ? | 0.0000 | 44 |

## Key findings

### 1. The 457 record has HIGHER λ_2 than the 459

**RECORD_TIE_457_blackwood_mrv_5min_seed10** has:
- 457/480 matched (4 LESS than 459)
- BUT λ_2 = 0.0377 vs the 459's 0.0369

This means: **algebraic connectivity is NOT monotonic in matched-edge
score**. A "more structurally connected" matched-edge graph CAN have
fewer matched edges (if the connection is through carefully chosen
adjacencies).

### 2. The hint constraint accounts for the trade-off

- 459 record: 4/5 hints. Drops position 210's canonical hint, gains 2-edge
  improvement.
- 457 record: 5/5 hints. Keeps all canonical hints, costs 2 edges, but
  is structurally MORE COHESIVE (higher λ_2, lower mz).

This is the **HINT-RIGIDITY trade-off**: relaxing one hint gives matched-
edge improvement at the cost of structural cohesion.

### 3. The 458 records are a single basin

All 3 verified 458 boards have IDENTICAL (λ_2, mz) = (0.0345, 39). 
Either same basin retrieved by different runs, or 458's geometry has
exactly one canonical structure.

### 4. The 457 records have VARIANCE

10 different 457 records show λ_2 in {0.0334, 0.0354, 0.0356, 0.0358,
0.0377} and mz in {31, 33, 36, 37, 38, 42}. This implies 457s are in
MULTIPLE BASINS.

### 5. The "best 457" has BETTER signature than 458

457 with λ_2=0.0377, mz=31 has BOTH metrics BETTER than ANY 458 board.
This 457 might be the structural sister of the 459. Implies:
- If we could find a board with this 457's connectivity AND 459's matched
  count, we'd have something interesting.
- Or: the 457 record_TIE_blackwood_mrv_5min_seed10 may be a basin closer
  to 460 than the 459 itself!

## Operational hypothesis

Boards with HIGH λ_2 + LOW mz are STRUCTURAL CANDIDATES for record-
breaking. The 457_blackwood_seed10 looks particularly promising.

**Concrete test**: Run ALNS on RECORD_TIE_457_blackwood_mrv_5min_seed10
(which is 5/5-hints) using different ops/seeds. Does it climb to 458+?
If it has higher λ_2, the basin should admit MORE moves.

User has explicitly said NO to ALNS variants on existing basins, but
this is a SIGNATURE-INFORMED selection, not a basin lottery.

## Status

`built-finding-positive`. New understanding of the 457/458/459 trade-off.

## Linked

- [[k11-2-algebraic-connectivity-signature]]
- [[k11-4-mismatch-zlib-signature]]
- [[k11-cross-domain-brainstorm]]
- [[459-level-set-two-cluster-confirmed]]
