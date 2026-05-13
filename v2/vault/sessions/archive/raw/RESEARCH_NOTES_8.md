# RESEARCH_NOTES_8.md — vol-8: community-export deep-dive

**Session**: 2026-05-12, single-thread.
**Mandate**: mine the user-provided `community-exports/` (groups.io archive
since 2000, Discord general channel since 2021) for ideas no academic paper
carries. Read-only on vol-7 artifacts.

**Corpus shape**:
- `community-exports/messages.jsonl` — 11,511 groups.io mailing-list
  messages, 2000-10-22 → 2026-01-… (~26 years).
- `community-exports/eternity2-discord-general.csv` — 1,198 Discord messages,
  2021-11-23 → 2026-01-24.
- Total: 221,706 body lines, ≈ 28 MB flat corpus.

**Infrastructure built**:
- `scripts/community_build_corpus.py` — flattens both sources into
  `output/v8_grep/corpus.txt`, every line prefixed
  `[<source>:<id>|<date>|<author>|<subject>] body`.
- `scripts/community_export_grep.sh` — 50-pattern mining battery,
  outputs one hit file per pattern in `output/v8_grep/hits/`.
- `scripts/community_extract_bucas.py` — decodes every
  `e2.bucas.name/#puzzle=...&board_edges=...` URL in the corpus,
  scores the canonical 480 internal joins, saves JSON + index TSV to
  `output/community_corpus/`.

**Verified-board corpus**: 123 bucas boards decoded; index at
`output/community_corpus/_index.tsv`. 78 boards ≥ 400 matched edges.

## Session log

### 09:55 — corpus built, first grep pass

Battery surfaces 41 mentions of `4[6-7][0-9]/480` (5-clue regime), 236 bucas
URLs, and 121 mentions of "tilab"/"2x3"/"2-by-3" (Verhaard's heuristic
vocabulary). Initial filtering by score and puzzle-tag separates the
canonical-E2 boards from variants (Blackwood unframed, Brendan-set,
Joe-17-color, etc.).

### 10:10 — verified canonical-E2 score ceiling

Among 17 boards tagged `puzzle=Eternity2` (canonical 16×16 Monckton set,
1..256 piece IDs verified by decoding `board_pieces=`), the highest
matched-edges count is **469/480 by Peter McGavin, 2020-09-09**, using
Joshua Blackwood's solver
(`https://github.com/jblackwood345/EternityII_Solver`). 256 pieces, all
distinct, range 1..256 confirmed programmatically. The next tier is **467
by multiple authors** (Verhaard's ceiling, matched by Bucas 2023 — these
are on `puzzle=E2nc` = E2-no-clue, not canonical 5-clue, so they don't
beat 469).

**This is +2 above the F1 agent's reported "Verhaard 467 ceiling" from
vol-7.** F1 was correct for *2008*, but **the community has held 469 on
canonical 5-clue since September 2020** — five years now. Vol-7's
recorded ceiling under-counts by 2.

Caveats:
- McGavin's `puzzle=Eternity2 / score=480` board (2023-10-09) is
  **fake**: it uses pieces from one E2 set + one Clue1 set + one Clue2
  set (`board_pieces=` contains numbers > 256: 308, 313, etc.). Title
  was "Competing for different tiles".
- McGavin's 448 "all 256 placed, no internal conflicts" (2023-03-11)
  is on the **unframed E2 variant** (outer edges deliberately wrong,
  admitted in the post). Doesn't count.
- McGavin's 471 / Razvan's 480 on `puzzle=16_16_set_1` / `puzzle=
  16x16x5x17_71.txt` are on **different piece sets** (Joe's 5-clue
  17-color variant, Brendan's puzzles) — not canonical.
- Blackwood's 470 (2021-03-30) and the corpus's two other 470 boards
  are on `Joshua_Blackwood_470` puzzle = 0-clue / Blackwood variant.
  This confirms the F1/memory finding that *Blackwood's 470 is not
  on 5-clue*, **but it adds: 470 on 5-clue is the goal of the active
  community (reinout_, onesmallstep) and they haven't reached it yet**.

### 10:30 — algorithmic vocabulary inventory

**Verhaard's actual method** (in his own words, groups.io 105190116,
2008-04-11):
> "Take a random group of maybe 180-190 pieces, use some method to
> determine the overall tilability of this group, and then gradually
> improve this group using by exchanging 'bad pieces' with better
> pieces using some appealing/annealing method until some local optimum
> is reached… From this 'good group' we take the 10-20 'worst
> performers' and try to find a solution of the initial 80 pieces using
> as much as possible from the 'loser group' and (as few as possible)
> 'worst good ones' and use this 80-piece solution as the initial basis
> for one small search."

The metric Verhaard validated: **solutions-to-a-2×2 patch count**,
O(n⁴), R² = 65% with log(total tilings) on a 2×22 random subset. This
is **not** the "2×3-tileability per piece" recorded in vol-7's memory;
it is **set-tilability via 2×2 sub-patches, optimised globally** by
swap-annealing. The vol-7 memory should be updated: the granularity
isn't per-piece banding, it is **piece-set composition** (which 180
pieces to commit to before backtracking).

**anr_56's Eulerian-cycle border theorem** (groups.io 105176464,
2007-06-28). Treat patterns as vertices, border tiles as directed
left→right edges in a multi-graph. A valid border ring ⇔ an Eulerian
cycle ⇔ in-degree = out-degree at every vertex *and the graph is
connected*. The first condition is automatic if left-pattern counts
equal right-pattern counts; the second is the **real** constraint.
Numerical result: random borders with even L-R counts tile with
probability 0.78 (P=15) or 0.70 (P=16). **We have a corpus of 100k
sampled borders from vol-6; nobody has applied the connectivity test
to them.** Cheap propagator: build the multi-graph for the current
partial border ring; reject any extension that disconnects it.

**Al Hopfer's "stall point" / "jump" observation** (groups.io
192928399, 2021-09-21). On a simple backtracker scanning rows: pieces
202-206 are a stall band; around piece 213+ a "good piece order" jumps
5-8 placements (e.g. 213 → 218 or 221) **then dies**. Maximum partials
from his framework are 221 placed (≈ 422 matched edges). Backup point
from 221 is around piece 69 — agreeing with our vol-6/vol-7 finding
that escape from a 449-region plateau requires deep restarts. His
"restrict pieces 139-256, run to 85-90 placed, then release" is a
**piece-budget warm start**.

**Knucklefinger's frame-first pessimism** (groups.io 105188617,
2008-03-01):
> "Placing a border first is suicide, because one is forcing the
> exposed sequence of the interior border."
Independent prediction of vol-6's finding that pinned-perimeter saturates
at 449-454. We had it as an empirical observation; the community
predicted it from first principles in 2008.

**Max + Verhaard "Robby the Robot" 2-phase scheme** (groups.io
105192402, 2008-08-27): "**backtracking with heuristics combined with
an endgame that allows mismatching**. I was quite surprised that I was
able to get beyond the 'don't-talk-about-limit' quite easily." This is
the **prototype of Blackwood's scheduled-conflicts-allowed mechanism**,
attested 12 years earlier. The 'don't-talk-about-limit' is the
contemporaneous high partial score (then ~458).

**onesmallstep's connection-list method** (Discord, 2026-01-24, rows
937-944). Live in-progress technique. For each border tile and each
known hint piece, enumerate which other tiles can connect via matching
edge colors. Example surfaced: "piece 62 doesn't connect to a hint and
also doesn't connect to piece 38; this reduces 62's placements to 170
tiles in one of four rotations depending on where 38 is." This is
**static AC-3 unit propagation** over the (piece, position, rotation)
lattice with hint pieces as seed. We do something equivalent in
`propagators::class_balance` but the *concrete inter-piece
incompatibility list* the community publishes is a data asset we don't
have — likely identical to what our propagators would compute on first
pass, but worth verifying.

**Mike Pringle + Peter McGavin "spiral with hints" (2026-01-10/11)** —
on `puzzle=16x16x5x17_71.txt` (Joe's 17-color variant, not canonical).
McGavin's brute-force scan-row solved it in 15 min with **just 18
strategically placed hints**; Pringle solved with 74 spiral-placed
hints. The technique is **scattering hints along the search path** so
the backtracker fans out earlier. Not directly transferable (different
piece set) but the **hint-placement-as-search-aid** angle is a
sub-puzzle decomposition we haven't tried on canonical E2.

### 10:50 — community technique catalogue (ranked)

See bottom of file for the ranked summary. Below are 1-line summaries
inline so the catalogue is easy to scan.

| # | Technique | Source | Cost | P(>454) | Δ vs vol-7 |
|---|---|---|---|---|---|
| 1 | Eulerian-cycle border connectivity propagator (anr_56) | groups.io 105176464 (2007) | 0.5d | 30-40% | new |
| 2 | Verhaard set-tilability **swap-annealing** with 2×2-count metric | groups.io 105190116 (2008) | 2-3d | 25-30% | corrects vol-7 memory |
| 3 | Phase-2 "allow mismatches" endgame (Max + Verhaard "Robby") | groups.io 105192402 (2008) | 1d | 15-20% | already partially built |
| 4 | Piece-budget warm start (Al Hopfer) — forbid 139-256, run to 90, release | groups.io 192928399 (2021) | 0.5d | 10-15% | new tactic |
| 5 | onesmallstep concrete inter-piece incompatibility list | Discord 2026-01 (live) | 1d to extract+ verify | 10% | adjunct to existing AC-3 |

Beyond the catalogue, two observations worth recording:

**The community's collective ceiling has *moved* on canonical 5-clue.**
467 (Verhaard 2008) → 469 (McGavin 2020 with Blackwood's solver). The
gain was algorithmic (Blackwood) + computational (McGavin's "couple
hundred cores for a few days"). Anywhere we sit ≥ 469 is genuinely
ahead of attested public state.

**No magic structural insight exists.** Across 11,511 messages over
26 years, no one has published a structural theorem that pre-localises
the obstruction. Knucklefinger's frame-first pessimism, anr_56's
border-tilability bound, and Verhaard's set-tilability are the three
sharpest analytical results; everything else is implementation craft.
This **agrees** with vol-7's structural findings: piece-level structure
is the unmodelled axis (M1+F1+X1 synthesis).

### 11:00 — falsifiable cross-checks vs vol-7 facts

1. **Rare-color opposite-edge rule** (vol-7 memory
   `project_e2_rare_opposite_rule.md`). Grep over corpus for `rare
   col*r` returns 1 hit (a chatty mention). The Selby-Riordan generator
   rule is not in community discussion. **Vol-7's discovery is
   genuinely original** — not just because it isn't in academic papers,
   but because the community didn't surface it in 26 years of
   discussion.
2. **30-mismatch budget** (vol-5/6 empirical). No community message
   discusses a *count* of forced mismatches; "13 breaks" (467) and "12
   breaks" (468 on Blackwood variant) are the operative units.
   **Mismatch budget framing is ours.**
3. **Selby's E2 generator countermeasures** (uniform color frequencies,
   GEMP-F phase transition). Three community messages reference Selby
   as the generator author, none discuss what the generator
   *optimises*. **Generator-space search remains an open frontier.**
4. **Deterministic PT ceiling on a given border** (vol-6 empirical).
   Multiple community messages observe analogous behaviour (Al Hopfer
   stall at 202-206; "the next edge permutation will find one in 1000
   moves" — Razvan groups.io 229349063). **This is a known phenomenon;
   our quantitative characterisation is new.**

## Findings summary (top 3-5 techniques)

**1. Eulerian-cycle border connectivity propagator** (P(>454) ≈ 30-40%
on its own, but compounding with existing PT). Build a directed
multi-graph from the current border-piece set's L-R edge patterns;
test for connectivity at every backtrack at depth ≤ 60. Connected ⇒
Eulerian cycle exists ⇒ ring closable. Disconnected ⇒ prune.
**Implementation**: `propagators::border_eulerian`, a single function;
the multi-graph has ≤ 22 vertices and ≤ 60 edges, so connectivity is
trivial. The strength comes from where in the tree the check fires.
Source: anr_56, 2007-06-28.

**2. Verhaard set-tilability swap-annealing** (P(>454) ≈ 25-30%, the
historical ceiling-mover). *Before* backtracking, run a cheap
simulated annealer over piece-set composition: pick 180-190 of the
196 interior pieces; metric is "count of 2×2 sub-tilings exhausted on
this set"; swap pieces between this set and the discarded 16-pair set;
keep the post-anneal "good 180". Then backtrack with the good 180
allowed and the worst 10-20 deferred to phase 2 with mismatches
allowed. **Implementation cost**: 2-3 days Rust. **Worth doing because
this is the *attested* algorithm behind Verhaard's 467 and was never
ported to a modern stack.** Source: louis.verhaard, 2008-04-11.

**3. Phase-2 mismatch-allowed endgame** (P(>454) ≈ 15-20% as a
standalone gain; subsumed by Blackwood-style scheduled-relaxation).
At a fixed depth (≈ 240-250 placed), permit a budget of k mismatches
on remaining placements. Pick a k schedule (e.g. k=1 from depth 240,
k=2 from 248, …). This is the prototype of Blackwood's scheduled
`conflicts_allowed`. We've recorded the technique; the implementation
in our PT path is straightforward and may already partially exist in
`crates/localsearch/src/repair.rs`. Source: Max + Verhaard, 2008-08-27.

**4. Piece-budget warm start** (P(>454) ≈ 10-15%). Forbid pieces
139-256, backtrack alone to ~85-90 placed (consistently reachable
according to Hopfer); then release the forbidden pieces and continue.
The mechanism: pre-shaping the upper-left region with the "easy" half
of the piece set, then letting the hard half fill around fixed
anchors. **Implementation cost**: 0.5 days; a flag on the existing
backtracker.

**5. onesmallstep concrete inter-piece incompatibility list**
(P(>454) ≈ 10%). Live Discord posting (Jan 2026) of the connectability
graph between numbered pieces. Likely identical to what our existing
AC-3 propagators compute on first pass, but **publishing the explicit
list lets us add it as a unit test for our propagator** and confirm we
aren't missing edges. **Cost**: 1 day to extract from Discord, format,
and write the regression test.

## Negative findings (worth recording)

- **No community claim above 469 on canonical 5-clue.** Naohiro
  Takahashi 468/480 (2009) was contested in 2017 (McGavin: "has his
  468/480 solution been verified and if so, how?") and never
  substantiated; no board posted. Treat as folklore until disproven.
- **"472/480" (henkvdg/trans.spam 2009-12) was *speculative***: the
  phrasing is "probably one of us reached 472" — collective optimism,
  no claim of personal achievement. Discount.
- **reinout_'s "471/480 partial edge matching score" (2026-01-20
  Discord) is a *goal statement***, not a claim: full message is
  "Getting a 231/256 linear score, getting a 471/480 partial edge
  matching score, finding good algorithms..." — three aspirations.
- **No Eternity I survivor (Selby, Riordan, Stertenbrink) ever posted
  the generator design** to the community list. The 5-color
  border-vs-17-color interior split is community knowledge, but the
  generator's *optimisation objective* is not. Inversion-attack
  (M1 from vol-7) remains the right angle.
- **No verified bucas board above 469 on canonical Eternity2 puzzle**
  exists in the entire 26-year corpus.

## What this changes about vol-7's plan

The X1+M1+F1 synthesis from vol-7 (piece-level structure is the
unmodelled axis) is **reinforced**, not contradicted, by vol-8. The
community converged on the same observation by 2008 (Verhaard's
set-tilability) and stalled. Three changes to the priority list:

1. **Verhaard set-tilability swap-annealing is a higher-priority port**
   than vol-7's "2×3 tileability ranking + depth-banded admission" —
   the actual algorithm is composition-level, not per-piece-temporal.
2. **The Eulerian-cycle border propagator is a cheap addition** that
   we could build today; it is genuinely novel for our codebase
   despite being 19 years old in the community.
3. **The 469 ceiling, not 467, is the canonical-5-clue community
   record**. Any vol-7 success metric should be calibrated to ≥ 469,
   not ≥ 467.

## Files / artifacts produced

- `RESEARCH_NOTES_8.md` — this file
- `scripts/community_build_corpus.py` — corpus builder
- `scripts/community_export_grep.sh` — mining battery
- `scripts/community_extract_bucas.py` — bucas URL → JSON board
- `output/v8_grep/corpus.txt` — flat searchable corpus (27.6 MB)
- `output/v8_grep/corpus_index.tsv` — per-message provenance
- `output/v8_grep/hits/*.txt` — 50 per-pattern hit files
- `output/community_corpus/_index.tsv` — 123 decoded boards, ranked
- `output/community_corpus/groups_*.json` + `discord_*.json` —
  the boards themselves

## Wayback-archived URLs

- `http://www.shortestpath.se/eii/eii_details.html` (Verhaard solver)
- `http://www.shortestpath.se/eii/results.html` (Verhaard results)
- `https://github.com/jblackwood345/EternityII_Solver` (Blackwood C#)
- `https://github.com/jfbucas/EternityII_Solver` (Bucas fork)
