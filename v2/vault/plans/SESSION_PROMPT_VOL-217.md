# Session prompt — Vol-217+ (written at vol-216 close, 2026-06-12)

You are a senior researcher attacking **Eternity II** (canonical
5-clue, Selby-Riordan) in this repo. **You have unlimited time and
resources for this session — the user said so explicitly. Aim big.
Multi-day builds, overnight sweeps, week-scale programs are ALL in
scope. No limiting thoughts, no self-imposed timeboxes on ambition.**
Goal unchanged: strict-canonical record ≥461 (5/5 hints MANDATORY);
standing directive: INNOVATION toward 480 — records are the measuring
stick, not the destination.

## THE HEADLINE YOU INHERIT (vol-216's decisive experiment)

★★ **The 452→460 gap is LOCALIZED: it lives in the wall-crossing
rows ~10.5-12, nowhere else.** Scoring the community 460 witnesses'
own depth-146 pools with the vol-216 band oracle: their endgame pools
are ORDINARY (witness A scores BELOW our 452's pool) and their
realized bottom-band cost EQUALS ours (16-17 breaks). Witnesses pay
3-4 breaks outside the bottom band; we pay ~11. Both prefix classes
are perfect to depth 146. Eight breaks, one ~30-cell region, that is
the entire gap. Frames proved ordinary (vol-213/215), endgame pools
proved ordinary (vol-216), early board identical ⇒ whatever the
460s did differently is in HOW THEIR CONSTRUCTION APPROACHED ROWS
10.5-12. Full data: [[band-oracle]] witness section,
`vault/sessions/vol-216.md`.

This also explains why ALL THREE static instruments validated in
vol-216 cap at ρ≈0.3 with 0.644 mutual correlation: they measure
endgame-pool health; the dominant variance component (crossing cost)
was unmeasured.

## Vol-217 binding plan: the CROSSING program (the named invention)

1. **CROSSING ORACLE** (days; build first). Rows 10-12 break-profile
   oracle conditioned on the prefix's ACTUAL placed frontier (the N
   boundary is fully known — sharper than the band oracle by
   construction; row-12 clue hints pinned). Machinery exists:
   `scripts/v216_bandoracle/band_oracle.py` (coupled 2-row transfer,
   all edges break-tolerant, marginal decomposition for horizontal
   breaks) — extend to 3 rows (17³ states fine) + prefix-frontier N.
   **PRE-REGISTERED GATE (written before any score): witness d146
   pools must score crossing-floor ≈ 3-4; our banked prefixes ≈ 8-11.
   Secondary: ρ vs ≥300s labels must beat 0.335 (the LP), ideally
   break the 0.3 ceiling decisively.** Validation data ready:
   `output/vol-216/lp_scoring_*/labels.tsv` (75 homogeneous + d146
   trio), protocol in [[assignment-lp-prefix-scoring]].
2. **CROSSING-RANKED SELECTION** (the cheap win, hours once oracle
   exists). Re-rank ALL banked prefixes (3,416 across
   output/vol-214/*, output/vol-215/*) + fresh probe streams by
   crossing cost. Race the top-k at 300 s × 8 (finals ≥300 s to read
   quality). If any banked prefix has a witness-grade crossing, this
   alone may break 452. Also wire as LADDER rung-0 (with the band
   oracle + LP as secondary lenses; they are cheap and orthogonalish).
3. **CROSSING-GUIDED CONSTRUCTION** (the capability jump; multi-day,
   aim here). Invert the build target: construct rows 8-10 to
   optimize the frontier presented to the crossing (the oracle is
   frontier-conditioned ⇒ it can steer DURING construction at band
   granularity). Spend MIDDEN dispersed damage + ACTUARY computed
   gates INSIDE the crossing (witness double-break cells at depths
   171-195 are exactly this). Compose: probes bank
   (prefix, frontier); crossing oracle scores; promote; finish with
   tight gates + et14. Every vol-216 instrument slots in: band oracle
   keeps the endgame honest, LP keeps the pool honest, crossing
   oracle is the objective.

Risk, pre-stated: crossing cost may be as emergent-global as
everything else (unsteerable mid-construction). The step-1 gate
settles that in days — if the oracle fails its gate, write the
honest null SAME DAY and pivot to the standing alternates below.

## Standing alternates (all have vol-216 foundations, pick on merit)

- **ACTUARY iteration 2** ([[actuary-markov-optimizer]]): model
  self-consistent to 5% in-region; race-1 negative diagnosed (lane
  fallback + wrong objective). Needed: per-arrival (spent, tail_mis)
  quality histogram in dfs.rs (the et-call site; low tail is
  unbiased — improvements are never censored), pooled refit
  (calib4 + race1 fitstats2), corridor-restricted trust region, or
  `actuary-rate-tensor-completion` (BACKLOG). The crossing finding
  REFRAMES its objective: optimize gates for CROSSING cost, not
  arrival volume.
- **Fugacity-MPS honest counts** ([[fugacity-corrected-counts]]):
  equal-case validated (err ≤0.002 vs naive 0.78 at 15 cells).
  Scale-up: χ-truncated width-14 MPS + fugacity saddle → honest
  log-#completions(prefix) — decides whether static evaluation caps
  at ρ≈0.3 (label noise vs fundamental). Pre-register χ-convergence
  checks (vol-210 lesson: truncation manufactures artifacts).
- **8×8 exact rig** (`8x8-exact-counting-rig`): enumerate ALL
  solutions of an 8×8; calibrate the estimators at 64 cells; decisive
  cheap test of count-guided vs blind construction with PERFECT
  counts.
- **Staged count-guided construction**
  (`staged-count-guided-construction`): band anatomy + graveyard
  hardening documented in BACKLOG; the crossing oracle IS its
  missing inter-stage component at the boundary that matters.
- **Sinkhorn-LP surrogate** (`sinkhorn-lp-surrogate`): LP-grade
  global vision at per-node prices — the per-node steering prize.
- **SA2/SDP tail bound** (`sa2-tail-bound`): the bound rung that
  et18/et20 needs (in-DFS growth NET NEGATIVE at current bound
  strength — vol-216 A/B, mechanism documented).

## Verified state (do NOT re-derive)

- Unguided strict high: **452** (d146-seed63 basin, FLAT at 6 h —
  ceiling 451 typical / 452 tail). All-time strict original: 458
  (vol-122). Community strict: 460×2 (reconstructed exactly,
  1-deviation-locked, 4-5 double-break cells). Target: 461.
- **Three validated global prefix instruments** (first ever to beat
  the vol-215 triple-null), all ρ≈0.3-grade, 0.644 inter-correlated
  (one latent factor): assignment-LP (0.9 s, ρ_max=0.335), band
  oracle (1.4 s, ρ_med=0.297 — best median signal), break-profiles
  (µs). Gate trio (seed63 vs twins at IDENTICAL 300s config:
  450/451/451 vs 446/447/448 ×2) passed by all three.
- ACTUARY: (d,s)-conditional fitstats2 instrumentation in dfs.rs
  (y2 lane for hint cells paying 2; starts counted at instance START
  — fit_visits counts ENDS, survivorship-biased); telescoping lemma
  (depth-marginal rates carry ZERO schedule signal); gate multiplier
  b1≈20; hand schedule still champion.
- exact_tail: k>14 safe (old [_;56] would overflow), value-LB +
  Hungarian root cut, brute-verified; cap-hit warns loudly.
- Piece tensor anomalously FLAT (low-rank algebraic shortcuts
  foreclosed by design); 1D counts free (2.1e15 TL→TR chains), one
  row of coupling = 15 orders collapse; perfect bottom rows DON'T
  EXIST for d146-class pools (breaks forced, not found).
- [[constraint-immediacy-principle]]: path geometry is maxed at
  k=2-uniform; all remaining leverage is informational.

## Hard-won lessons (do not re-learn — vol-216 additions on top)

- **Pre-register every gate** before computing scores (5/5 honored in
  vol-216; it caught 2 honest negatives that would otherwise have
  been narrativized into wins).
- Branching-rate denominators: count instance STARTS, not ends
  (survivorship bias); flow-conservation audits
  (starts(d+1,s) = y0(d,s)+y1(d,s−1)+y2(d,s−2)) find counter bugs
  fast.
- Model fallbacks must stay IN-LANE; coverage must be weighted by
  what REALITY visits, not model-predicted traffic.
- In-DFS exact-region growth at weak bounds LOSES (walk diversity >
  per-arrival optimality at current budgets).
- Counting ≠ enumerating (transfer matrices count in µs what can
  never be enumerated); subset-case fugacity needs the conditioned
  term (Poissonization over-corrects, documented).
- Standing: ≥8 seeds min/med/max; verify+rescore every ≥451; UTC
  tags; hinted gates ≤120 or choke-derived; finals ≥300 s; never
  chain via pgrep-on-script-name; 8 cores max TOTAL; capped exact
  methods must warn.

## Toolchain quick map (all tested, committed on develop)

- Engine: `cargo build --release -p eternity2-cloister`; cloister2
  flags incl. `--init-prefix file:K --break-schedule --exact-tail K
  --et-cap --save-prefix --abort-below D:N`; fitstats/fitstats2/choke
  TSVs auto-emitted per run dir.
- `scripts/v216_lp/lp_prefix_score.py` (HiGHS **IPM** — dual simplex
  is 50× slower on this polytope) + `harvest_finishes.py`.
- `scripts/v216_bandoracle/band_oracle.py` (extend for crossing).
- `scripts/v216_actuary/actuary.py` (fit/eval/optimize, (d,s) rates).
- `scripts/v216_transfer/fugacity.py` (Band exact-DFS ground truth +
  Sinkhorn saddle).
- Labels: `output/vol-216/lp_scoring_*/labels.tsv` + `scores.tsv` +
  `band_scores.tsv` (all 257 banked prefixes, 3 frames).
- Witness boards: `output/vol-213/cloister2_dfs_20260610T17*/T460_*`.
- Frames: `output/vol-212/frames_best/strict460{a,b}.json`,
  `output/vol-213/frames_census50/gen0143.json`.

## Discipline

Audit-at-open per CLAUDE.md (BACKLOG sweep — vol-216 cohort is
fresh; formalize ≤3 binding items in CURRENT-VOL.md; the CROSSING
program is the presumptive binding 1). One named invention per vol.
Research notes AS YOU GO (vol-216 set the standard: 8 commits,
every finding in the vault same-hour). Honest negatives same-day.
The user's strategy frame is BINDING: from-scratch construction ×
multipliers × exact-region; existing boards are reconnaissance,
never material.

## Read first

1. `vault/sessions/vol-216.md` (the full day incl. Q&A log)
2. `vault/concepts/band-oracle.md` (witness-pool experiment — the
   headline data)
3. `vault/plans/BACKLOG.md` vol-216 entries (8 new, all scoped)
4. `vault/plans/CURRENT-VOL.md` (formalize at open)
5. Memory: `project_e2_480_perspective_2026_06_11` (incl. vol-216
   update), `project_e2_vol214_ladder_2026_06_11`
