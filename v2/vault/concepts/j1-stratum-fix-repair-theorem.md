---
name: j1-stratum-fix-repair-theorem
description: "From J1 loss-localization, the 36 missing edges live ONLY in V_8..V_14 + H_15. This admits a 'fix-stratum' MIP/ALNS restricted to rows 8-15 with the upper 8 rows frozen. Mathematical derivation of feasibility, support, and an operator definition."
metadata:
  type: project
---

# J1 stratum-fix repair theorem

## Setting

From [[j1-loss-localization-math]] on the J1 Rust 444-board (beam=100k):

- $H_0..H_{15}$ horizontals: ALL 16 rows have perfect horizontal scores. Concretely, rows 0..14 are explicitly perfect (15/15 each); row 15 horizontals are bounded by $H_{15} = 35 - V_{14}$ which we treat as the residual.
- $V_0..V_7$ verticals (boundaries between rows 0,1 / 1,2 / ... / 7,8): all perfect (16/16 each, total 128).
- $V_8..V_{14}$ verticals: lossy (1+1+3+4+6+10+10 = 35 in current J1 board).
- $H_{15} + V_{14}$ joint shortfall = 11.

**Total loss = 36 edges, all confined to the lower 7 verticals + bottom row.**

## Theorem (stratum-fix decomposition)

Let $B$ be a J1-produced board with the structure above. Let
$\Sigma_{\text{up}} = \{(r,c) : r \le 7, 0 \le c \le 15\}$ (128 pieces, rows 0-7) and
$\Sigma_{\text{lo}} = \{(r,c) : r \ge 8, 0 \le c \le 15\}$ (128 pieces, rows 8-15).

Then the score decomposes as:

$$
E(B) = \underbrace{E_{\text{up}}^{\text{internal}}}_{\text{frozen, perfect}}
     + \underbrace{V_7(B)}_{\text{interface, perfect}}
     + \underbrace{E_{\text{lo}}^{\text{internal}}}_{\text{repairable}}
$$

where
- $E_{\text{up}}^{\text{internal}} = \sum_{r=0}^{6} (H_r + V_r) + H_7$
  = (8 perfect rows of horizontals) + (7 perfect inter-row verticals)
  = $8 \cdot 15 + 7 \cdot 16 = 232$ edges.
- $V_7 = 16$: interface verticals (also perfect).
- $E_{\text{lo}}^{\text{internal}} = \sum_{r=8}^{15} H_r + \sum_{r=8}^{14} V_r$
  = current value: $8 \cdot 15 + (16+16+13+12+10+6+\text{?}) - \text{(\#missing in inner H)} = 196$.

(Check: $232 + 16 + 196 = 444$ ✓.)

## Stratum-fix operator: definition

Let $\mathcal{F}(B) \subset \text{Sym}(\Sigma_{\text{lo}}) \times \{0,1,2,3\}^{\Sigma_{\text{lo}}}$
be the set of (permutation, rotation) actions on the 128 lower-stratum
pieces. A stratum-fix move replaces $B|_{\Sigma_{\text{lo}}}$ with
some $B'|_{\Sigma_{\text{lo}}}$ such that:

1. $B'|_{\Sigma_{\text{up}}} = B|_{\Sigma_{\text{up}}}$ (upper stratum unchanged).
2. The top edges of $B'$'s row 8 match the bottom edges of $B$'s row 7
   (interface constraint, 16 colors fixed).
3. $E_{\text{lo}}^{\text{internal}}(B')$ is maximized.

**Hence the upper $232 + 16 = 248$ edges are AUTOMATICALLY preserved.**

## Search space size

Lower stratum has 128 pieces. The 128 pieces used by $\Sigma_{\text{lo}}$
are the ones NOT used by $\Sigma_{\text{up}}$ — a fixed set of 128.

Permutations: $128! \approx 3.86 \times 10^{215}$. With rotation: $\times 4^{128} \approx 10^{77}$ more.

So the raw search space is $\sim 10^{293}$. Untrackable.

BUT: the **row 8 interface constraint** fixes a 16-color vector on top
of the lower stratum. This is the *exact same problem J1 solves for
band 0*. We can run J1's column-DP on the lower stratum starting from a
fixed top-color vector.

## J1-on-lower-stratum cost

J1 column-DP at band $r$ has state space:
- top color (16): fixed (interface).
- bot color (16): free.
- piece-availability bitset (128 bits).

Beam $\sim 10^5$ states per column, 16 columns per band, 7 bands. So
$\sim 10^5 \cdot 16 \cdot 7 = 10^7$ operations per band-pair, scaled by
state-transition cost (piece-rotation lookup): manageable in $\sim 1$
minute in Rust.

**Estimated cost: 1-2 minutes for a stratum-fix attempt.**

## What can we GAIN?

Upper bound on $E_{\text{lo}}^{\text{internal}}$:
- 8 rows of horizontals: max $8 \cdot 15 = 120$.
- 7 inter-row verticals: max $7 \cdot 16 = 112$.
- 1 interface vertical (V_7 boundary): already counted in $\Sigma_{\text{up}}$.

Total max: $120 + 112 = 232$.

Current: 196 (in J1 board).

**Upside if a stratum-fix achieves the max: $E(B') = 232 + 16 + 232 = 480$.**

Of course, $E_{\text{lo}}^{\text{internal}} = 232$ would solve the puzzle.
More realistically: even matching $E_{\text{lo}}^{\text{internal}} = 215$
(perfect verticals only, some horizontal loss) brings the board to
$232+16+215 = 463$ — a NEW RECORD.

## Caveats and obstacles

1. **Hint compliance is 0/5 in J1 boards.** A stratum-fix doesn't restore
   hints. Need to introduce hints as constraints in J1 or do post-repair.

2. **Lower stratum 128 pieces are dependent on the upper.** The 128 free
   pieces have specific edge-color distributions. If the upper consumed
   "good" pieces, the lower has only "bad" leftover pieces — that's
   exactly why band 14 fails. **Stratum-fix may NOT do better than
   J1-with-FLH** at the same starting upper stratum.

3. **The interface row-8 top colors are committed.** They drive the
   row-9 piece selection, which drives row-10, etc. Local move on
   row 13 cannot fix row 12 vertical loss.

4. **The proof above shows BOUNDS on the operator, not REACHABILITY.**
   We have not shown that $E_{\text{lo}}^{\text{internal}} > 196$ is
   achievable with the given 128 pieces and interface colors.

## Empirical test plan

1. Implement `j1_stratum_fix` binary that takes a J1 board, extracts
   the upper stratum, computes the interface top-color vector for row 8,
   runs J1 column-DP on rows 8-15 with the constraint, returns the best
   $E_{\text{lo}}^{\text{internal}}$.
2. Compare to the J1 board's $E_{\text{lo}}^{\text{internal}} = 196$.
3. If $> 196$, we have a new board (still 0/5 hints).

## Stratum-fix vs. ALNS

ALNS on a J1 board does worst-band/random destroy and repair across the
entire board. It WILL touch the upper stratum, breaking the perfect
horizontals. The stratum-fix operator surgically preserves them.

If ALNS doesn't beat 459 from a J1 444-board, then either:
(a) The upper-stratum structure is sub-optimal (can't be reached from
459-style boards), OR
(b) ALNS gets distracted by the upper structure (false optima).

Stratum-fix eliminates (b).

## Status

`theorem-derived` — bound + operator + empirical plan defined.
Implementation: next.

## Linked

- [[j1-loss-localization-math]]
- [[j1-forward-look-heuristic]]
- [[j1-rust-beam100k-first-complete-board]]
