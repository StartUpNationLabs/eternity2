
Solve canonical 5-clue Selby-Riordan Eternity II (16×16, 22 colors, 5
canonical hints) by INVENTING genuinely new algorithms / mathematical
approaches / structural insights. The current community ceiling is 469/480
(McGavin 2020 via Blackwood's algorithm); our project's standing record is
459 on the 4/5-matched-edges convention. Target: BEAT 469 — solve the
puzzle (480/480) or break the community SOTA decisively.

OPERATING MODE: senior researcher in charge.
- Read v2/ONBOARDING.md FIRST. It documents every consolidated tool
(load_board, save_board, verify_board, score_board, board_convert,
print_bucas, diff_boards) plus pipeline recipes, score conventions,
the 459 problem state, and the canonical bins.
- Then read v2/CLAUDE.md (role rules), v2/vault/INDEX.md (knowledge
map), and the most recent vault/sessions/vol-NN.md.
- ALWAYS use canonical eternity2_export APIs. Never write a per-bin
load_board / score function. The 14 duplicates were consolidated in
vol-118 T9; don't reintroduce them.

WHAT "INVENT" MEANS (binding, per 2026-05-16 user directive):
1. Do the MATH when math is the bottleneck. Pencil-and-paper a bound,
 derive a polytope, prove a lemma, attack the structure directly.
 Math notes go in vault/MATH_NOTES_<date>_<topic>.md or
 vault/concepts/<analysis>.md.
 2. INVENT new algorithms, not variants of named methods. Give each
 invention a fresh name. Negative results are acceptable IF the
 invention itself was novel.
3. NO comfort-lottery patterns (same operator + new seed + new budget
 ≠ progress). If you find yourself in one, pivot to genuinely new
 structure.
4. NO LIMITING THOUGHTS on ambition. "Multi-day work" is in scope. If
 an idea seems "weeks-long," just START — don't pre-estimate.
5. Take research notes AS YOU GO. Every non-trivial derivation,
 conjecture, or measurement → vault/concepts/ or vault/sessions/
 *at the moment it occurs*, not at session close.

OPEN HANDHOLDS (unrefuted, ranked by EV):
- RL self-play with reward = max-score (multi-week, only unrefuted
theoretical handhold per vol-114).
- Cutting-plane LP/MIP for tighter UB (multi-week per vol-47).
- MaxSAT/SMT on the full mismatch-cluster region (cluster_maxsat_repair
exists for halo-1; never run on 459 mid-region clusters at scale).
- Hint-aware schedule recalibration (vol-117 T5 sketch, post-conflict
-fix priority).
- New basin discovery via systematic corner-perm + seed-offset sweep
with bound-ascent UB filter (would extend the 459 corpus).

EXPLICIT NON-NEGOTIABLES:
- ALWAYS run verify_board on any board you produce. Border-violation
detection catches the vol-118 bf-bucket-bug class.
- ALWAYS verify-then-diff before claiming "same board" or "new basin."
- Use `basic` preset for ALNS record-track work (memory: basic > winning5).
- Strict-canonical convention requires hints_obeyed = 5/5. The
pipeline that achieves this is documented in ONBOARDING.md §7.
- NEVER amend the existing 459/469 records (vol-118 T12 confirmed
them all clean).

DELIVERABLES (continuous, not "at end"):
- Commits to develop branch with prefix: "vol-XXX TY: <one-line>".
- Vault concept page per non-trivial finding.
- Session journal at vault/sessions/vol-NN.md.
- If you discover a record (matched-edges ≥ 460 with 4/5 hints, OR
strict-canonical ≥ 458, OR 1-clue ≥ 471, OR ANY 480/480) — write a
PAPER-LEVEL writeup at vault/PAPER_<date>_<title>.md AND share via
share_onboarding_guide / commit message.
