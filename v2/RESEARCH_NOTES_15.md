# RESEARCH_NOTES_15.md — vol-15 session log

**Opened**: 2026-05-12, ~18:20 CEST (verified via `date`).
**Status**: open.
**Reads completed at start**:

- `MEMORY.md` (full index).
- `project_e2_vol14_session_summary.md` — vol-14 one-pager.
- `project_e2_vol14_rectangle_path_findings.md` — the user's
  "fail-fast around hints" insight that frames vol-15's
  priorities.
- `project_e2_vol14_alns_hint_bug.md` — the critical bug whose
  fix invalidates pre-fix vol-12/vol-14 scores; baselines must
  be re-derived on the patched binary.
- `project_e2_mcgavin_blackwood_gap_analysis.md` — what our
  stack is missing to reach 469.
- `RESEARCH_NOTES_15_PLAN.md` — the priority list.
- `V15_BLACKWOOD_SPEC.md` — full implementation spec for #1.
- `V15_FRAME_ENUMERATOR_SPEC.md` — implementation spec for #3.
- `project_e2_vol12_engine_profiles.md` — current engine
  registry the new code has to extend.

## Calibration anchor (vol-14 closeout)

| metric                                          | score |
|-------------------------------------------------|------:|
| baseline `joe_depth150_par` + ALNS-fill         | 442/480 (broken-binary; ~440 on fixed) |
| BP-seeded baseline + ALNS-fill                  | 443/480 (broken-binary; ~440 on fixed) |
| vol-6 PT-from-453 (PT had correct pinning)      | 454/480 |
| community SOTA (McGavin 2020)                   | 469/480 |

**Vol-14 honest cold-start best ≈ 440/480**, NOT 443 as previously
reported. Re-run with patched `alns_e2` is the prereq for any
fair vol-15 A/B.

## Vol-15 anchor commitment

**Priority 1 — Blackwood algorithm**. This is the only deliverable
in the priority list that has a path past the "without Blackwood
ceiling" of 446–454. Plus 1.5 (Blackwood × HintRectangle
composition) as a 4-hour follow-up once #1 lands.

Why this and not Priority 2 (hint-cluster sub-CSP enumeration):
sub-CSP enumeration is cheap and gives 0–15 matched-edge gain
without learning. Blackwood encodes the compile-time
"fail-fast against a global schedule" mechanism that the user's
vol-14 hint-rectangle hypothesis pointed at. McGavin/Blackwood
gap-analysis: until at least #1+#2+#3 (heuristic schedule +
break-index + in-place restart) ship, our ceiling stays at
446–454. Vol-15 must close the schedule gap first.

## Plan (in order)

1. Validate baseline. Re-run `joe_depth150_bp_par` + patched
   `alns_e2` once to get a fresh honest cold-start baseline on
   the fixed binary. Recorded as the vol-15 scoreboard reference.
   Pipelined alongside Blackwood implementation work.
2. Implement Blackwood per `V15_BLACKWOOD_SPEC.md` tasks
   B.1 → B.6 in `crates/solver-engine` (keep it on develop;
   don't create a separate crate — the spec actually says
   solver-engine extensions; vol-15 plan says
   `crates/solver-blackwood/` mirroring solver-verhaard would
   be acceptable; the engine-extension path is cheaper and the
   schedule lives naturally inside `EngineConfig`).
3. Unit-test the new pieces on synthetic small puzzles.
4. Validate on 12×12/12 testbed (8 seeds × 90s) before scaling.
   Beat baseline 247/264 with majority ≥ 255/264 ⇒ scale.
5. Canonical E2 pilot at 500M-iter scale.
6. Closeout block with Tier ranking and vol-16 recs.

## Bars

- Tier 1: ≥454/480 standalone Blackwood ⇒ catches up to vol-6.
- Tier 2: ≥469/480 ⇒ ties community SOTA.
- Tier 3: ≥470/480 ⇒ clears community SOTA.
- Tier 4: 480/480 ⇒ out of scope without McGavin throughput.

## Live log

(appended below as session progresses)

---
