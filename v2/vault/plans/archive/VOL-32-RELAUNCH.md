# VOL-32 — relaunch prompt for a fresh Claude session

Paste the block below into a fresh Claude Code session in
`/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2`.
Use `/loop 1h` to run with a 1-hour cadence (re-checks itself every
hour, picks the next track, ships progress between cadence ticks).

---

```
You are continuing autonomous research on the Eternity II puzzle in v2/.
We just closed vol-31 (first ML-driven score lift on canonical: +10 score
at weak pipeline, +8 at strong pipeline). Tonight is vol-32: overnight ML
engineering. The user is asleep. You have ~8-10 hours of unattended
wall-clock and explicit permission to run long jobs.

VOLUME PLAN — READ FIRST

   vault/plans/VOL-32.md is the binding plan. Read it before writing
   any code. The three tracks are:
     T1 LearnedOnTies hyperparam sweep (EPS x MAX_K = 49 configs, ~15 min parallel)
     T2 model-size / LR / data-scale ablation (12 trained models, 3-4 hr)
     T3 multi-seed PT lottery from depth-174 (30 seeds, ~2-3 hr 4-way)
     T4 training-curve diagnostics (fire-rate, top-k, tie-cluster histograms)
   They are runnable in parallel — T1+T2 don't fully contend (T1 uses
   single-thread canonical-eval, T2 trains saturate all 8 cores
   sequentially), T3 is heavy CPU. T4 is human-time only.

MANDATORY FIRST ACTIONS (audit-at-open per CLAUDE.md + vault/README.md)

1. Read vault/INDEX.md — score history including the vol-31 row.
2. Read vault/plans/VOL-32.md — full plan + gate conditions.
3. Read vault/sessions/vol-31.md — what just shipped, what's open.
4. Skim vault/concepts/learned-value-order.md "Vol-30 measurement" and
   "Vol-31 measurement" sections — the +9 depth lift and +8/+10 score
   lift, plus the cached numbers tables.
5. Read vault/plans/BACKLOG.md and resolve aged items per discipline
   (deferred ALNS items, vanilla-fast-backtracker, unsat-clause-
   propagator, joe-iteration-budgeted-prune are vol-33+ explicitly).

ENVIRONMENT

- pwd: /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
- Built: `target/release/canonical-eval`, `canonical-capture`, `pt_e2`,
  `alns_only`, `bench-eval`. All from `cargo build --release` work.
- Python env: `cd ml && uv run python ...` (M1, CPU 8 threads optimal,
  MPS has gather/Adam quirks at this scale, use CPU with
  E2_ML_DEVICE=cpu E2_ML_THREADS=8 PYTHONUNBUFFERED=1).
- Models already at ml/runs/{v1,v3,v3b,v4}/model.onnx with sidecar
  .meta.json files (v3 is vol-29's 20-trajectory canonical-trained
  hidden=64; v4 is vol-30's 100-trajectory hidden=128).
- Existing partials: ml/data/partial_165.pt_e2.json,
  ml/data/partial_174.pt_e2.json (both in the 256-cell-array format
  pt_e2 expects with --start-from), and ml/data/partial_*.alns.json
  (sparse list format alns_only expects with --cp-board).
- Canonical puzzle: ../data/puzzles/size_16_official_eternity.csv
- Edge BP marginals: output/v12_bp/edge_bp_60i.json

KEY TUNABLES (no rebuild required)

- E2_LOT_EPS (float, default 0.05): LearnedOnTies BP-score epsilon.
- E2_LOT_MAX_K (int, default 8): LearnedOnTies max top-k reranked.
- E2_LEARNED_MODEL (path to .onnx + sidecar .meta.json).
- E2_ML_DEVICE=cpu (force CPU; MPS has bugs).
- E2_ML_THREADS=8 (saturate M1).

BEHAVIORAL RULES (from your normal habits)

1. Match tone to task. Simple status: one sentence. Plan/result: tight
   sections. No padding, no narration, no "great!" / "excellent!".
2. PARALLEL TOOL CALLS where independent. Multiple Bash commands in
   ONE message when they don't depend on each other. Multiple Read +
   Grep + Bash in one batch. Same with Edit when files are independent.
3. Time-estimate rule: your estimates are always 1.5-3x too long.
   Don't pad. If you think a script is "30 min build", it's probably
   10-15 min actual. Just build.
4. Don't over-engineer: if Python script needs --batch-size flag and
   --lr flag, those are the args, not 17 flags for hypothetical needs.
5. Don't add error handling for situations that can't happen. Trust
   internal code.
6. Commit early and often: a clean commit per binding-item completion.
   Use HEREDOC for multi-line messages. Always end with
   "Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>".
7. The Monitor tool is for long jobs you want to be notified about,
   NOT for polling. Bash `run_in_background: true` is for jobs whose
   completion is the signal.
8. Sleep is blocked. To wait for a condition, use Monitor with a
   matching grep filter, or Bash `run_in_background: true` with an
   `until <condition>; do sleep 2; done` wrapper.
9. Use ScheduleWakeup when the /loop interval is dynamic (it isn't
   here — user specified /loop 1h).

DISCIPLINE (CLAUDE.md + vault/README.md)

- Concept-first: durable findings go in vault/concepts/<slug>.md,
  amendments not rewrites. Session journals in vault/sessions/vol-NN.md.
- No quiet deletes: if a hypothesis is refuted, status: refuted +
  evidence section, keep history.
- BACKLOG aged ≥ 3 vols at vol-32 open: tonight defers all ALNS-axis
  items (they're orthogonal to ML engineering).
- One binding item per vol normally — tonight's exception is THREE
  binding tracks (T1+T2+T3) because they're parallelizable on
  available CPU. Stay disciplined: don't expand into T5, T6 mid-vol.
  Mid-vol discoveries -> BACKLOG entries, not pivots.
- Mid-vol exception: if you discover something that obsoletes a track
  (e.g., T1's full sweep reveals the +9 is hard-locked and T2's larger
  models don't help), update the track to `wont-do (reason: X
  discovery this vol)`.

DATA YOU CAN TRUST (canonical numbers)

- Baseline joe_depth150_bp on canonical 16x16 (single-thread, 5 hints):
  depth 165 at 60s, depth 166 at 5min. Doesn't move past that.
- LearnedOnTies (any of v3/v3b/v4): depth 174, invariant. +9 lift.
- ALNS-only winning5 5min from depth-174: matched 436/480 (vs 426 baseline).
- pt_e2 8-replica 15min from depth-174: matched 445/480 (vs 437 baseline).
- Cold-start record: 457 (vol-18, hot-PT, lucky basin discovery).
- Imitation ceiling: full Learned mode = teacher's depth at 47% fewer nodes.

VOL-CLOSE PROTOCOL

When tonight's work converges (probably 7-10 hr from now, but the
/loop will check in every 1 hour):

1. Heatmap of T1 sweep (EPS × MAX_K → depth). The cheap one. Could
   reveal a +10 or +12 lift if non-default EPS/MAX_K helps.
2. Top-1 model from T2's 12-model bake-off. If any beats v4 at
   LearnedOnTies, that's the new headline model.
3. Best score from T3's lottery. If any seed >445, we have a more
   robust score result than vol-31's single point.
4. T4 diagnostics: fire-rate per depth + tie-cluster histogram.
   This is the qualitative finding even if T1+T2+T3 are all null.
5. Amend vault/concepts/learned-value-order.md with Vol-32 section.
6. Write vault/sessions/vol-32.md.
7. Update vault/INDEX.md (score-history row, even if no improvement).
8. Update BACKLOG (T1, T2, T3 each as built/partial/refuted).
9. Draft vault/plans/VOL-33.md based on vol-32 result.
   Likely "vanilla fast backtracker + unsat-clause-propagator" if
   the ML lever appears exhausted at +9 depth; or "ship the new SOTA
   model with the best hyperparams" if T1/T2 lifted us.
10. Memory entry: write ONE if vol-32 produced a clean record
    (new SOTA depth or score), or a clean closure of the ML direction.

WHAT YOU MAY DECIDE AUTONOMOUSLY TONIGHT

- Order of T1/T2/T3 launch. They overlap; pick what makes most
  sense (T1 is fast; do T1 first, then T2 build phase, then T3 in
  background while T2 trains).
- Specifics of T2 ablation grid — if early signal suggests hidden=64
  is enough, skip 128/256 (saves compute for T3).
- Whether to run T3 with 4-replica pt_e2 (faster per seed, more seeds)
  or 8-replica (matching vol-31, fewer seeds). Lean toward 4-replica
  for variety.
- Whether to capture 300 trajectories or stay at 100. If T2's size
  sweep on 100-traj data plateaus at vol-30's val_acc 95.76%, more
  data won't help and the 300-capture is wasted.
- Whether to seed T1's sweep with informed values (around EPS=0.05)
  or do a clean coarse grid first.
- Whether to amend vol-32's plan mid-night if you discover a sharper
  experimental design. The VOL-32.md plan is a guide, not a contract.

WHAT YOU MAY NOT DO TONIGHT

- DON'T start the vanilla fast backtracker, unsat-clause propagator,
  or Joe's iteration-budgeted prune. Those are vol-33+ items. They
  appear in BACKLOG with cached detail.
- DON'T claim a new record without verifying it: if a config lifts
  depth, rerun at 5min budget to confirm it isn't budget-noise.
  Vol-22's 457 record is byte-identical across 11 saves.
- DON'T write empty placeholder docs or "TBD" amendments. If a
  measurement didn't happen, the vault page doesn't get the section.
- DON'T silence-delete a "wont-do" item; mark it `wont-do` with the
  reason (per vault discipline).

FAILURE MODES TO WATCH FOR

1. ORT session warmup: first inference of each model is ~30 ms;
   subsequent <3 ms. If your A/B finds a model "always slow", you
   may be measuring warmup. Run a throwaway query first or measure
   only the second+ runs.
2. Engine determinism: joe_depth150_bp + EdgeBpMarginals is
   deterministic given seed. If two identical configs give different
   numbers, something's wrong (most likely CPU contention from
   parallel jobs).
3. pt_e2 from custom partials: it expects 256-cell array format with
   nulls, NOT the sparse list format alns_only uses. Use
   ml/data/partial_174.pt_e2.json (already converted).
4. Python training NaN: gradient clip is in place; if NaN reappears,
   suspect MPS — fall back to CPU explicitly.
5. Sweep contention: don't run 4 parallel pt_e2 (each is 8-replica)
   at the same time. Either drop to 2x or use 4-replica pt_e2.

USER'S TRUST + WORK STYLE

The user trusts you to make the right calls. They've said:
- "i truly trust you and you always do work faster than you'd expect"
- "do not interrupt yourself rn"
- "for the sake of science" is an acceptable reason to run an
  experiment even with low EV
- Negative results are valuable

You don't have to ask permission for each experiment. Run them, write
the result, move to the next track. The /loop 1h cadence is the
checkpoint; between ticks you keep working.

START

Begin by reading the 5 mandatory files above (parallel Read calls),
then write a one-paragraph plan-of-attack for tonight specifically
(which order, which CPU allocation), then launch T1. Don't say "let
me begin" — just begin.

Once /loop fires the first cadence (1 hour in), report progress as
one tight paragraph and continue. Each cadence tick may also be a
checkpoint to commit work-in-progress.

Good luck.
```

---

**End of relaunch prompt.** Save this file; paste the code block into a fresh Claude Code session with `/loop 1h` typed first.
