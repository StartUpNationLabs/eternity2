# CDCL no-good learning for E2 — design + soundness

**Status**: `design` (math only, no code) — vol-56 (2026-05-15).
**Origin**: Vol-56 T2. Closes a long-standing gap: solver-engine
discards all conflict information at backtrack. No-good learning is
the classic CSP/SAT technique for harvesting that information.

## Setting

The E2 CSP as currently implemented in `solver-engine`:
- **Variables**: cell positions $c \in [0, N^2)$ for $N = 16$.
- **Domain** $D_c$: set of $(p, r)$ placements compatible with
  cell-class (corner/edge/interior). For interior cells with all
  pieces still available, $|D_c| = 192 \times 4 = 768$. After AC-3
  $D_c$ shrinks.
- **Constraints**:
  1. **All-different on pieces** (each piece used $\le 1$ time): for
     all $c \ne c'$, $\sigma(c).p \ne \sigma(c').p$ where $\sigma$ is
     an assignment.
  2. **Edge-equality** (for each adjacent pair $(c, c')$ with sides
     $(s, s')$ facing each other, the touching colors agree): see
     `propagate_ac3` in `solver-engine/src/lib.rs`.

The search problem is **MaxCSP**: find a (partial) assignment
$\sigma: C' \to D$ with $C' \subseteq C$ maximising the score
$$S(\sigma) = \#\{ \text{internal edges } (c, c') : c, c' \in C' \text{ and edges match} \}.$$

(The current engine in `--mode best` returns the highest-$S$ partial
it visits; `--mode first` returns the first $\sigma$ assigning all
cells, regardless of mismatches.)

## What a no-good is for E2

A **no-good** is a set of placement-literals
$$N = \{(c_1, p_1, r_1), (c_2, p_2, r_2), \ldots, (c_k, p_k, r_k)\}$$
together with a **bound** $B \in \mathbb{N}$:

> "No extension of $N$ to a complete assignment achieves score $> B$."

Equivalently, for any total $\sigma$ with $\sigma(c_i) = (p_i, r_i)$ for
$i = 1, \ldots, k$, we have $S(\sigma) \le B$.

**Special case** ($B = 0$, "hard no-good"): no extension of $N$ to a
total feasible assignment exists at all (some constraint is violated
in every completion). The classic CSP no-good.

**Soft no-good** ($B > 0$): completions exist but cap at $B$ edges.
The MaxCSP generalisation.

## Sources of no-goods (how to learn them)

### Source 1 — hard, from AC-3 wipeout

When AC-3 reduces some cell domain to $\emptyset$ during search, the
current partial assignment is infeasible. The no-good
$N = \{(c, \sigma(c)) : c \text{ currently assigned}\}$ with $B = 0$
is sound: no completion of this exact assignment is feasible.

This is the **trivial no-good**. Used naively it's the same as
backtracking. To be useful, **minimise** $N$ to a smaller set still
implying $B = 0$.

### Source 2 — MaxCSP from incumbent score

If at any node the engine has reached score $S(\sigma_\text{partial})$
plus an upper bound $U$ on the remaining edges (e.g.
[[relaxed-bound]]), then any completion has $S \le S_\text{partial}
+ U$. If $S_\text{partial} + U \le B_\text{best}$ (the best score
found so far, our incumbent), no improvement is possible from this
node. The no-good is the current partial assignment with $B =
S_\text{partial} + U$.

### Source 3 — implication-graph analysis (CDCL proper)

The classic SAT CDCL move: when a conflict is detected, walk the
implication graph backward to find the *minimal* set of literals
responsible. In E2, the propagators (AC-3, NS-1, parity) provide
implication links: if propagator $P$ removed value $v$ from $D_c$
because of currently-assigned literals $L_1, \ldots, L_m$, then those
$L_i$ are the cause.

The 1-UIP (first unique implication point) analysis from SAT carries
over: walk back to the first node where exactly one literal from the
current decision level is in the cut. That gives the asserting clause.

For E2, the implication tracking would be:
- AC-3 removes $(p, r)$ from $D_{c'}$ because $(p, r)$ is incompatible
  with currently-assigned $(c, p_c, r_c)$ via edge-equality. Implication:
  $(c, p_c, r_c) \Rightarrow \lnot (c', p, r)$.
- Piece-uniqueness removes $(p, r)$ from $D_{c'}$ because piece $p$ is
  already used at $(c, p, r_c)$. Implication:
  $(c, p, *) \Rightarrow \lnot (c', p, *)$.

## Soundness

**Lemma (hard no-good)**: If during search with partial assignment
$\sigma_\text{partial}$ AC-3 wipes out cell $c$ (some $|D_c| = 0$),
then any extension of $\sigma_\text{partial}$ (in particular any
$\sigma \supseteq \sigma_\text{partial}$) is infeasible.

*Proof*: AC-3 only removes a value $(p, r)$ from $D_c$ when there's no
$(p_{c'}, r_{c'}) \in D_{c'}$ compatible with $(p, r)$ for some
neighbour $c'$. This is monotone: extending $\sigma_\text{partial}$ to
more cells can only further restrict the propagator's neighbour
domains, so $|D_c|$ stays $0$. Since $c$ must be assigned in any total
$\sigma$, no total extension exists. □

**Lemma (soft no-good)**: If at node $\sigma_\text{partial}$ the
incumbent score is $B^* = B_\text{best}$, the partial score is
$S_p = S(\sigma_\text{partial})$, and an admissible upper bound on
remaining edges is $U$, then any extension $\sigma$ satisfies
$S(\sigma) \le S_p + U$. If $S_p + U \le B^*$, the no-good
$(\sigma_\text{partial}, B = S_p + U)$ is sound: any extension matches
the bound and is no improvement.

*Proof*: trivial from the bound's admissibility.

**Lemma (no-good minimisation, hard case)**: Let $N$ be a hard no-good
and let $N' \subseteq N$ be a sub-assignment such that AC-3 applied to
$N'$ alone produces an empty domain. Then $N'$ is itself a sound hard
no-good.

*Proof*: AC-3 from $N'$ on a less-constrained sub-problem produces an
empty domain $\Rightarrow$ no completion of $N'$ is feasible
$\Rightarrow$ any super-assignment $N \supseteq N'$ is also infeasible.
$\square$

## Propagation rule

After learning a no-good $N$, we want fast pruning during future
search. The propagation rule:

**Rule**: If at a search node, $k - 1$ of the $k$ literals in $N$ are
assigned and consistent (all $(c_i, p_i, r_i)$ in $N$ match the current
$\sigma$), and one literal $(c_j, p_j, r_j)$ is unassigned, then:
- For hard no-goods ($B = 0$): remove $(p_j, r_j)$ from $D_{c_j}$.
- For soft no-goods ($B > 0$): if completing $N$ would force a node
  with $S \le B$ and $B < B^*$ already, remove $(p_j, r_j)$ from
  $D_{c_j}$.

If $k$ literals are assigned and consistent, the current $\sigma$
extends $N$ and we either backtrack (hard) or compute the implied
score bound (soft).

This is the **unit-propagation rule** generalised from SAT.

## Indexing / storage scheme

The naive store is a list of no-goods, checked at every search node —
$O(|\text{no-goods}| \cdot k)$ work per node, prohibitively expensive
at canonical scale.

The classical SAT trick: **two-watched-literals** (2WL). For each
no-good $N$, watch any two of its literals. When a watched literal
becomes unassignable, find another to watch; if you can't, the
no-good is fully assigned in $\sigma$ except possibly one literal, so
propagate.

For E2 the literals are $(c, p, r)$ triples. The watch index is keyed
by $(c, p, r)$ → list of no-goods watching this triple. When a value
is removed from $D_c$ during AC-3, we walk the watch list and update.

Memory: each no-good takes $O(k)$ space; the watch index is $O(1)$
per no-good (just 2 watches). For 1M learned no-goods of average size
20, the storage is ~20-40 MB. Tractable.

## Engine integration sketch

In `solver-engine/src/lib.rs`:

1. **Conflict detection**: extend `propagate_ac3` to return not just
   "feasible/infeasible" but, when infeasible, the set of literals
   responsible (the conflict cause).

2. **Learn**: on infeasibility, run 1-UIP analysis to derive the
   minimal no-good. Store in a `NoGoodDB`.

3. **Check**: at each `recurse` call (or at AC-3 entry), traverse
   the watch list for the newly-added literal $(c, p, r)$; for each
   no-good in the list, check if the second watch can be advanced
   or if the no-good fires.

4. **Forget heuristic**: classic CDCL has periodic clause deletion to
   keep the DB bounded. Heuristic: delete no-goods with low recent
   activity (LBD or activity-based).

5. **Restarts**: classic CDCL restarts on a luby schedule. For E2,
   restart corresponds to clearing the search tree but keeping the
   no-good DB. The vol-50 node_budget axis is the right hook —
   restart on node_budget instead of time.

## Why this is genuinely novel for E2

Vol-26-29 ML imitation: ceiling at teacher.
Vol-48-49 RL/ES: refuted (argmax invariance).
Vol-22 basin-escape: validated but ALNS-saturation bottleneck.
Vol-44/55 MIP: confirms local optimality, doesn't break record.
**No-good learning: untouched**. CDCL-on-CSP is well-established in
the SAT community (e.g., MAC + nogood-learning in CSP solvers); we
have NEVER applied it to E2.

The key bet: the canonical-E2 search tree has **structural failures
that repeat** (e.g., specific 3-cell sub-assignments that can never
complete). Learning these once and pruning them everywhere should
compound to a meaningful speedup, possibly enabling deeper search →
higher partials → more ALNS candidates.

Critically, **no-good learning preserves soundness** by construction.
Any record found by an engine with no-good learning is provably valid
(unlike ML where train-distribution drift can corrupt outputs).

## Subtlety — soft no-good "minimality" is not trivial

After writing the design above, I realised the soft no-good case
needs more care. Stating the assertion precisely:

A **soft no-good** is a pair $(N, B)$ where $N$ is a partial
assignment and $B$ is a bound, asserting:
$$\forall \sigma \supseteq N : S(\sigma) \le B.$$

The "useful" minimal version is: find the **smallest** $N$ such that
any completion of $N$ (alone) has $S \le B$. This is strictly harder
than the hard-no-good minimisation:

- For HARD no-goods, AC-3 re-applied to any $N' \subseteq N$ either
  produces an empty domain (still infeasible) or not (became
  satisfiable by removing constraints). Easy test.

- For SOFT no-goods, removing literals from $N$ relaxes the
  bound — the relaxed-bound on completions of $N'$ might be $> B$
  even though completions of $N \supseteq N'$ are at most $B$.
  **Not monotone.**

What this means: 1-UIP for soft no-goods isn't a straightforward
adaptation. We can still learn the trivial soft no-good (full
$\sigma_\text{partial}$ with $B = S_p + U$), but minimisation
requires either:
- LP-relaxation argument (e.g., dropping literal $\ell$ from $N$
  is sound iff the relaxed-bound on $N \setminus \{\ell\}$ is
  still $\le B$). Can be computed but costs ~1 LP per minimisation
  attempt.
- Or just store non-minimal soft no-goods and accept the size cost.

**Practical recommendation**: for the MVP, only learn HARD
no-goods (from AC-3 wipeout) at first. Defer soft-no-good learning
to a later iteration once the hard case works. This is consistent
with how SAT CDCL evolved historically (only unit-propagation-based
learning, no "score" no-goods).

## Open questions / for vol-57 build

1. **AC-3 implication tracking**: solver-engine's AC-3 doesn't
   currently record *why* it removed a value. Adding this is the
   first engineering hurdle. Cost: re-implementing AC-3's queue
   loop with cause-tracking. ~1 week.

2. **Minimal no-good extraction**: the 1-UIP analysis has subtle
   correctness conditions in MaxCSP setting (vs pure CSP). Need
   to verify carefully.

3. **Watch-list maintenance under restarts**: when the tree clears,
   the watch list of literals to which we've never returned still
   needs valid pointers. Standard CDCL handles this via a "level
   stack"; we'll need an analog.

4. **Soft no-good activation gating**: soft no-goods are score-
   dependent; their soundness depends on the incumbent $B^*$. When
   $B^*$ improves, some soft no-goods become inactive (their bound
   no longer prunes). Need to handle this correctly without rescanning
   the whole DB.

5. **Interaction with vol-32 InsertionOrder / vol-50 node_budget**:
   different value orderings change which conflicts arise first.
   No-good DB carries over across different mode/profile choices;
   this is a strength but needs testing.

6. **Solver-engine no-good budget**: bound DB size; pick a
   forget-policy.

## Estimated build cost (multi-week, per usual)

- AC-3 cause-tracking refactor: 1 week.
- 1-UIP minimisation: 3-5 days.
- 2WL watch index: 2-3 days.
- Forget heuristic + tuning: 2-3 days.
- Integration testing on small puzzles (6×6/5c): 2-3 days.
- Canonical-E2 measurement: 2 days.

Total: 3-4 weeks. Per user's "limiting thoughts" feedback,
MVP-overnight-doable is possible: a pure-Python prototype on a
small puzzle could be ~1-2 days. Decision: this vol-56 is math;
vol-57 will pick whether to MVP-prototype or full build.

## Linked

- [[../sessions/vol-56]] — this vol's session journal
- [[../sessions/vol-55]] — predecessor; closed LP-tightening arc
- [[../concepts/relaxed-bound]] — admissible upper bound for soft no-goods
- [[../concepts/prune-restart]] — vol-23/51 prune-restart; conceptually
  adjacent (both throw out part of search and retry)
- memory: `feedback_autonomous_dont_wait.md`, `feedback_no_limiting_thoughts.md`
