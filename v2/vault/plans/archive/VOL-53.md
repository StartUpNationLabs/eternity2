# Current vol — vol-53 (queued, not yet started) — 2026-05-15

**Predecessor**: vol-52 closed with the per-piece column-gen design
doc ([[lifted-lp-column-gen-per-piece]]).

**Status note (autonomous session honesty)**: I (the autonomous agent)
closed vols 50, 51, 52 in this run. Vol-53 is queued but not started;
the binding item below is the right next move but needs ~2-3 days of
focused Python work + numerical-debugging time. Starting it at the
end of an already-long session would produce poor-quality output. The
next session (user-or-autonomous) can pick this up cleanly.

## Vol-53 binding item — concrete 6×6/5c worked example of per-piece column-gen

Vol-52's design doc sketched a 6×6/5c worked example abstractly.
Vol-53 makes it concrete:

1. **Pick a specific 6×6/5c instance** that has an LP-integer gap
   (i.e., LP UB > integer best). Run vol-46's LP-UB tool on a
   handful of 6×6/5c puzzles and find one with a measurable gap.

2. **Enumerate the per-piece columns** in Python — a small script
   that for each piece, computes its set of feasible placements
   given border + hints.

3. **Run column-generation in Python** with HiGHS via `highspy` (no
   Rust required for the proof-of-concept). Iterate the master LP
   + pricing until convergence.

4. **Show the math**: starting LP UB = X, after column-gen LP UB = Y < X.
   Y should be very close to the integer best (closing the gap).

5. **Write up findings** in a new concept page:
   `vault/concepts/per-piece-column-gen-6x6-worked.md`. Include
   the actual numbers, the convergence trajectory, and the
   estimated extrapolation to 16×16.

### Why this matters

If the math works at 6×6 (closes most of the gap), it's strong
evidence the 16×16 build is worth the 7-10 day engineering investment.

If the math FAILS at 6×6 (gap doesn't close), the vol-52 design is
refuted — saves the 7-10 day build entirely.

Either way, vol-53 produces decisive information.

### Risk budget

- **1 day**: pick puzzle, Python script (~100 lines), run column-gen,
  write up.
- **2-day kill-switch**: if column-gen doesn't converge or produces
  obviously wrong bounds, characterise the failure mode and stop.

### Out of scope

- Rust implementation (still vol-54+ if vol-53 validates).
- 16×16/22c measurement (engineering cost too high without
  validation).

## Audit-at-open

Same aged items as vol-52; defer all (vol-53 is design-validation,
not picking from BACKLOG).

## Linked

- [[lifted-lp-column-gen-per-piece]] — the design to validate
- [[vol-52]] — predecessor
- [[lp-integer-gap-anatomy]] — vol-50 motivation
