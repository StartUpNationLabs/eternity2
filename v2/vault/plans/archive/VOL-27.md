# VOL-27 — Eliminate bridge overhead + retest gate at harder scale

**Opened**: 2026-05-13 (vol-26 close).
**Status**: drafted; awaits open.
**Gated on**: vol-26 result. The 540× algorithmic win is real; the stdio
bridge eats it. The vol-26 gate failed on a technicality (condition (c)
unsatisfiable at 6×6/5c since MRV had zero failures); the substantive
finding is unambiguous.

## Why this volume exists

Vol-26 measured:
- 540× engine-node reduction at 6×6/5c (clean win).
- 56× wall-clock SLOWDOWN due to stdio JSON + Python torch overhead.
- Gate condition (c) unsatisfiable at 6×6/5c (MRV 200/200 solved).

The diffusion direction is alive at small scale algorithmically, dead
at small scale operationally. Vol-27 closes both gaps:
1. **Remove the bridge.** Get inference cost down to a few microseconds
   per node so the algorithmic win surfaces as a wall-clock win.
2. **Retest at 7×7 / 8×8.** Where MRV has real failures, condition (c)
   is meaningful.

## Audit-at-open

Vol-26 explicitly waived this (chronology inversion with vol-25). Vol-27
MUST audit. Items aged ≥ 3 volumes by vol-27 open:

- `piece-orbit-as-atom` (7 vols, vol-20). Likely `wont-do`.
- `multi-cell-bound-ascent` (5 vols, vol-22).
- `bound-floor-alns-with-per-step-check` (5 vols, partial).
- `kissat-rc2-maxsat` (4 vols).
- `diverse-457-search` (5 vols, partial).
- Anything aged from vol-25's audit.

Action at vol-27 open: read each, make a decision in writing in BACKLOG.

## Binding items

### T1 — Eliminate the bridge (in-process inference)

Three implementation routes, pick ONE:

**Route A — ONNX export + `ort` crate in Rust (RECOMMENDED).**
- Export `model.pt` to ONNX via `torch.onnx.export`.
- Add `ort = "2"` to `crates/solver-engine`'s dev-deps (or new
  `ml-runtime` crate to keep solver-engine clean).
- Replace `bridge::LearnedBridge` with an `OnnxScorer` that loads the
  `.onnx` once at solver construction and runs inference on a
  `Vec<f32>` feature buffer directly.
- Honest cost: ~1 day if ONNX export hits no quirks; ~3 days if our
  `GridConv` gather pattern doesn't translate cleanly (ONNX may
  require explicit gather indices; we can rewrite the conv to use them).

**Route B — PyO3 in-process Python.**
- `maturin develop` to build a Python extension; keep model in PyTorch.
- Removes IPC, gives direct tensor access. Still has GIL overhead.
- Honest cost: ~2-3 days because of build setup + tensor lifetime
  management across the FFI boundary.

**Route C — hand-rolled f32 Rust forward.**
- 53 k params is tiny. Write `forward(feats: &[f32; N*13]) -> [f32; 144]`
  directly against a `Vec<f32>` weight buffer loaded from `model.pt`.
- Removes Python entirely. Risk: subtle FP divergence from trained model;
  must verify equivalence on 100+ test inputs.
- Honest cost: ~1-2 days.

### T2 — Retest gate at 7×7 / 8×8 / 5c

After T1 succeeds:
- Retrain the model at 7×7/5c (training data already cheap to produce —
  ~5-10 min for 3k puzzles given vol-26's measure-difficulty numbers).
- Run the same gate spec. At 7×7/5c, MRV has ~7% failure rate within
  5s budget → condition (c) is meaningful.
- If gate passes (all three): the diffusion direction is **alive at
  intermediate scale**, vol-28 plans canonical 16×16 transfer.
- If gate fails: report which conditions failed and why. If (b) fails
  because in-process inference is still slower than LCV, the direction
  is dead at this scale.

### Item budget cap

2 binding items max (T1 + T2). T1 unblocks T2; without T1 there's no
honest re-measurement.

## What this vol explicitly does NOT do

- ❌ Canonical 16×16 evaluation. Defer to vol-28 conditional on T2 pass.
- ❌ Self-play / RL / fancier architectures. T1's job is the bridge,
  not the algorithm.
- ❌ Variable-size model architecture. The today's GNN is fine at fixed
  sizes; rewriting it is vol-28+ scope.
- ❌ Comparison vs `EdgeBpMarginals` or `BlackwoodHeuristic`. Vol-26
  compared to `LeastConstraining`; staying with that for apples-to-apples.

## Discoveries during the vol → log, don't pivot

Per CLAUDE.md vault discipline. The pull during vol-27 will be:
- "Let's just go straight to canonical 16×16." — NO. Vol-26 didn't
  measure on canonical at all; we have no evidence the imitation
  signal transfers.
- "Let's also try diffusion." — NO. Imitation already gives 540× at
  6×6; the bridge is the bottleneck, not the model class.

Log both to BACKLOG with `since: vol-27`.

## Vol-close protocol

1. Update T1+T2 status in BACKLOG.
2. Amend `[[learned-value-order]]` with the new wall-clock numbers
   from T1's in-process inference. Add a `## Vol-27 measurement`
   section.
3. If T2 ran: add the 7×7/8×8 gate result table.
4. Write `sessions/vol-27.md`.
5. Update `INDEX.md` score-history row (still "no record change",
   but note the methodology result).
6. Memory entry only if T2 changes the gate conclusion (PASS → vol-28
   canonical transfer becomes viable; FAIL → close the ML direction).

## Honest cost estimate

- Route A (ONNX): 1-3 days.
- T2 retrain + gate: 0.5 day given T1's plumbing.
- Audit-at-open + writeup: 0.5 day.

**Total: 2-4 days.** Single sitting plausible if ONNX export goes
smoothly.

## Why this is the right shape

Vol-26 produced a clear algorithmic signal masked by an engineering
problem. Vol-27 is engineering-bounded with a clean re-measurement on
the same gate spec. Information-per-hour is high: 2-4 days resolve the
"is ML alive on E2-family puzzles" question definitively.

After vol-27:
- If T1+T2 pass: vol-28 planning targets canonical 16×16 transfer (much
  harder; requires variable-size model + size-invariant training).
- If T1 fixes wall-clock but T2 fails (b): the direction is dead because
  in-process inference is fundamentally slower than CP heuristics.
- If T1 doesn't fix wall-clock (e.g., ONNX export breaks on `GridConv`'s
  gather pattern and the fallbacks don't help): the direction is
  blocked on ML-runtime engineering that's bigger than 1 volume can fix.
  Recommend close.

## Linked concepts

- [[learned-value-order]] — vol-26 gate result, baseline.
- [[synthetic-puzzle-generator]] — data source, unchanged.
- [[edge-bp-marginals]] — historical analog (BP-as-value-order).

## Linked sessions

- [[vol-26]] — direct predecessor.
- [[vol-25]] — the parallel engine-perf push.
