# Research notes — vol. 2

Continuation of `RESEARCH_NOTES.md`. Vol. 1 ends with the 2026-05-11 SESSION CLOSE summary, which is the right place to read first for context.

## Starting state (2026-05-11)

- Best on official Eternity II: **449/480 (93.5%)** matched edges, in ~3 minutes (30s CP + greedy_fill + 180s PT).
- Community SOTA: 467/480 (97.3%) — Verhaard 2008.
- The 446-449 plateau is structural; pure local-search saturates here regardless of move set.

## Methodology rule (carried over from vol. 1)

Every experiment writes one section here with:
- **H** — hypothesis in one sentence.
- **Setup** — corpus, runs/cell, profiles compared.
- **Result** — JSON path + headline numbers (median ms, nodes, backtracks).
- **Verdict** — kept / dropped / iterated, with one-line reason.

Negative results count. Numbers from the same corpus under the same budget are required for "successful".

---

## Mindset for this volume

- Take time. Long-horizon research is expected.
- Reformulate. If a problem feels stuck, ask: which other field has solved a structurally-equivalent problem? Math ↔ geometry ↔ graph ↔ physics ↔ logic ↔ algebra. Translation often unlocks the move that's invisible from inside the original framing.
- Cheap experiments first. 30-line diagnostics can falsify expensive hypotheses.
- Trust strong negative results — when N variants of approach X all hit the same number, that's a theorem, not noise. Change approach class, not parameters.

---

## (entries follow as experiments run)
