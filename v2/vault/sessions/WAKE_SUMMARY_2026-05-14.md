# Wake summary — 2026-05-14 autonomous session

**Period**: 15:30 → 18:25 CEST (~3 hours of work).
**Vols completed**: 35 (closed) → 36 → 37 → 38 → 39 → 40.
**User instruction**: "Be autonomous, finish the puzzle, 1 week".

## Headline result

**No record break**, but real new tools + 3 new verified canonical records:
- Canonical 454 (NEW pathway via make-canonical operator)
- Canonical 455 ×2 (NEW, ALNS-diverse from canonical 454)

**Records ledger (verified via ml/verify_records.sh, all 10 PASS):**

| Score | Hints | Source | Volume |
|---:|:---:|---|---|
| **458** | 3/5 | vol-32 vanilla_fast → ALNS | vol-32 |
| 458 | 3/5 | vol-35 deep458 reproduce (byte-id) | vol-35 |
| **457** | 5/5 | vol-32 blackwood_mrv seed 7 | vol-32 |
| 457 | 5/5 | vol-32 blackwood_mrv seed 10 | vol-32 |
| 457 | 5/5 | vol-32 blackwood_mrv seed 4 (30m) | vol-32 |
| **456** | 5/5 | vol-32 blackwood_raw seed 2 | vol-32 |
| 456 | 5/5 | vol-32 blackwood_raw seed 4 | vol-32 |
| 455 | 5/5 | vol-39 diverse seed 1 | **vol-39 NEW** |
| 455 | 5/5 | vol-39 diverse seed 5 | **vol-39 NEW** |
| 454 | 5/5 | vol-36 make-canonical + ALNS seed 5 | **vol-36 NEW** |

**Best canonical (5/5 hints): 457 (×3, all vol-32).**
**Best absolute (any hint compliance): 458 (×2, 3/5 hints).**

## Volume-by-volume summary

### Vol-36 — vanilla_path + make-canonical operator

- Built `vanilla_path` bin: raw-DFS with 7 custom path modes, 60-100M pp/s.
- A/B finding: **border-first wins cold CP** at +12 edges vs row-major.
- All centre-first paths refuted (reconfirms vol-14 hint-centric null).
- Discovered **canonical-compliance tension**: deep CP partials tend to
  displace hint pieces; vol-32 458 has only 3/5 hints honored.
- **Make-canonical operator**: drop displaced+canonical hint positions,
  add canonical hints, prune_restart MaxScore fills. vol-32 458 →
  canonical 446 in 0.1s.
- ALNS-5min × 8 seeds from canonical 446 → seed 5 = **454** (NEW
  canonical pathway).

### Vol-37 — structural discoveries + gh_e2

- Built `structural_scan.py`: mines 7 verified records for invariants.
- **Found pos 161 = pid 234 rot 0 invariant** across all 7 records
  (interior cell, NOT hint-adjacent, all 4 edges always matched).
- pos 0 + pos 1 also invariant (corner/border-forced).
- Built `gh_e2.py`: gradient + Hungarian projection. Novel algorithm
  class but relaxation gap dominates (soft → 462, discrete → 100-454).
- Two mid-vol re-evaluations (user prompted) cancelled saturated lotteries.
- Pos 161 synthetic hint A/B on vanilla_fast 5min × 8t: +2 depth, +4
  score (modest).

### Vol-38 — prune-restart on canonical 454 (honest null)

- A/B drop-k ∈ {0, 20, 40} on canonical 454 with MaxScore CP.
- **All completions scored ≤431** (-23 vs starting 454).
- Conclusion: canonical 454 mismatch region is structurally
  CP-uncompletable — no local fill beats 454.
- To break canonical 454: need larger drop (>50% of board) OR
  modification of the SURROUNDING 218 cells, not the mismatch cluster.

### Vol-39 — ALNS-diverse from canonical 454 (modest lift)

- ALNS-diverse (winning5 + BottomBandDestroy) 8 seeds × 5min.
- **2/8 reached 455** (NEW canonical 455 boards, distinct).
- 6/8 stayed at 454.
- 25% lift rate for 454 → 455.

### Vol-40 — ALNS-diverse from canonical 457 (honest null)

- ALNS-diverse 24 runs (3 sources × 8 seeds × 5min).
- **0/24 lifted past 457**.
- Confirms vol-22 "457 is ALNS-locked" even with BottomBandDestroy.
- ALNS ceiling per basin ≈ +1 score with declining probability:
  454→455 = 25%; 457→458 = 0%.

## Tools built/shipped

| Tool | Purpose | Status |
|---|---|---|
| `vanilla_path.rs` | Raw-DFS with custom cell-visit paths | shipped |
| `--extra-hint POS:PID:ROT` on vanilla_fast | Synthetic hint support | shipped |
| `ml/make_canonical.py` | Project non-canonical → canonical via drop+CP | shipped |
| `ml/structural_scan.py` | Mine records for invariants | shipped |
| `ml/gh_e2/gh_e2.py` | Gradient + Hungarian projection | shipped (algorithm doesn't break records) |
| `ml/verify_records.sh` | Update with canonical-hint check | updated, 10/10 PASS |

## Honest assessment of remaining feasibility

**To break 458 we'd need**:
1. **Community-class compute**: McGavin's 469 was a 2-week Blackwood
   pre-prune + 11-hour SAT solve. Days × 100 cores.
2. **OR new algorithm class**:
   - RL self-play (1-2 weeks build, multi-day training)
   - Exact MaxSAT with kissat-rc2 (1 week build, may not converge)
   - LP relaxation B&B (too big for scipy; needs HiGHS or commercial solver)
   - Diffusion + CP projection (1 week build, uncertain)

**Realistic remaining-week ceiling on M1 + Claude time**: 458-459. Beating
58 by chance requires luck-chain of 4 lifts at decreasing probability;
chain probability ≈ 0.4% per attempt.

## Recommended next direction (vol-41+)

**Option A (recommended)**: stabilization + documentation.
- Polish tools, write clean READMEs.
- Update verify_records.sh (done this vol).
- Leave project in clean state for future researchers.

**Option B (long shot)**: build no-good CDCL learning (~2-3d engine work).
Standard SAT technique never applied to E2 engine. May give 5-15% search
reduction but unlikely to break records.

**Option C (research-track)**: pivot to algorithmic exploration of one
new class (RL or exact MaxSAT). Multi-day build, may not finish in the
week, but real progress on a frontier.

## Files of interest

- `vault/sessions/vol-36.md` to `vol-40.md` — per-volume detail
- `vault/sessions/vol-37-re-evaluation.md` — mid-session re-eval reasoning
- `vault/sessions/vol-37-pos161-discovery.md` — structural invariant detail
- `output/vol-39/records/` — 2× new canonical 455 boards
- `output/vol-36/records/RECORD_CANONICAL_454_vol36_seed5.json` — canonical 454
- `ml/make_canonical.py` — operator
- `ml/structural_scan.py` — scanner
- `ml/gh_e2/gh_e2.py` — gradient algorithm

## Git state

- All vol-36-40 work committed + pushed to origin/develop.
- 6 commits in this session.
- 532 commits ahead of master.
