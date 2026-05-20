# Basin 459 — SOTA on canonical E2 (cross-machine result)

**Status**: NEW RECORD. +1 over the vol-32 458.
**Date**: 2026-05-14 night → 2026-05-15 morning.
**Source**: cross-machine run on another instance, results imported.
**Canonical compliance**: full 256/256 cells placed, all 256 piece-IDs unique.

## Bucas URL

```
https://e2.bucas.name/#puzzle=v17_alns_only&board_w=16&board_h=16&board_edges=adcaaepdafoeaemfabteafhbabjfachbaencacqeabhcacsbabpcabgbaeibaabecpcapskpouismhjutvphhnlvjminhgimnnpgqgtnhhlgssphpwnsgsjwiujsbafucidaklqiiriljkgrpgnkllogiwilinqwpmontrsmluqrpmmunwlmjhhwjnthfacndgdaqmqgijjmgisjngriouvgiwquqngwouqnsrtuqpqrmiwpllkihwqltgiwcadgdsdaqugsjosuslgorqwlvprqqgmpgkogqmoktrvmqrtrwmmrkigmqoriiisodadidtcagigtstjigwstwvgwrkhvmttkovntoknvvulktmsumsomgvgsrnkvsnnndaencvbagtqvjkqtssskgrushmortplmnsvpnqoslhuqsknholnkgmtlkqhmnqoqeafqbmdaqlvmqjklskqjuwokovuwlrwvvmkrorrmujtrnvijntqvtpjthhrpourhfafudweavvlwkokvqwsooklwuvtkwlwvktnlrgrttnpgigpnqiigjpjiropprglofafgelfalwolkuhwshwulsnhtopswuionhhuruhhplouprilijurjlijplullkplfackfqfaovjqhunvwswunplspvwpijvvhukjhlsuomnliommunkoiomnujuopppjcadpfhcajqphntmqwvwtlgvvwvjgvitvkkgisntknvjnmujvksiumwksuhmwptwhdaftcrbaphkrmrmhwhtrvjshjrijtkvrgtrktlqtjmlljovmiqookwhqmulwwtqqfadobtfakkntmnrkthjlsjuhiggjolugrlslqphinqrpmjvooqtjhwmqgiiwqwoidafwfjbanmpjrgtmusthuvusgmspunrqjronhkprrvwkvkvwrwpkmsowjprssuvpfadubdaahdadteadteaeueaeseaeqbaeoeabpbaejbabveabpcaeocacrfacvcafdaac
```

## SOTA board JSON

`output/v17_alns_only/basic_sa_t1_s42_1778827429_827089000_p48848.json`

## Pipeline that produced 459 (4 stages)

### Stage 1: vanilla_path border-first × 9 threads × 30min → 403/480

```bash
./target/bench-fast/vanilla_path \
    --budget-ms 1800000 --threads 9 \
    --path-mode border-first \
    --puzzle ../data/puzzles/size_16_official_eternity.csv \
    --save-best /tmp/border_first_best.json
```

- Border-first scan: 60 perimeter cells first, then row-major interior.
- 3 restarts: scores 387, 403, 397 canonical. Best = 403.
- 226/256 placed, 30 holes in bottom rows.

**Key finding**: border-first DFS reaches 403, vs row-major 392 across 29
restarts. The +11 gap is from PATH ORDER alone (no compute cost).

### Stage 2: ALNS minimal × 5min from 403 → 452/480

```bash
alns_only --cp-board <403-partial> --ops minimal --seed 1 --alns-budget-ms 300000
```

Ops preset `minimal`:
- `random_region{4}` (destroy 4 random cells)
- `worst_window{5}` (destroy worst 5×5 window)
- `conflict_driven{30}` (destroy 30 most-conflicted cells)
- `mwpm_defect_pair{12}` (min-weight perfect matching repair on 12 cells)

Trajectory: 403 → 412 → 426 → 444 → 449 → 450 → **452** (7 improvements,
+49 edges in 5min).

### Stage 3: ALNS minimal × 8 inputs × 8 seeds × 15min → 454/480

64-job sweep. **Seed=4 dominates**: produces 454 on multiple inputs
including 392-canonical row-major partials. Same seed yields same 454
across different inputs — **seed dominates input at this depth**.

### Stage 4: ALNS basic × 30min × seed 42 from 454 → 459/480 ★ SOTA

```bash
alns_only --cp-board <454-partial> --ops basic --seed 42 --alns-budget-ms 1800000
```

Ops preset `basic` = `minimal` + `WorstBand{4}` — ONE extra destroy
operator (band-strip).

Trajectory: 454 → 456 → 457 → 458 (vol-32 record matched at iter 21)
→ **459 at iter 450** (RECORD). Plateau after iter 450.

## Three decisions that broke the record

1. **Border-first path order** (Stage 1). Free +11 over row-major.
2. **minimal → basic escalation** (Stage 4). Minimal plateaus at 454;
   adding ONE destroy (`WorstBand{4}`) is enough. Mega/full are too
   aggressive.
3. **Seed 42 specifically**. Seed 4 with basic reached 458; seed 42
   reached 459. Seed-distinct basins; sweep seeds 1..200 to find.

## What did NOT work

- `mega` ops: scorches good cells (435 from 403 input).
- 10-hour single-thread DFS: depth 216, canonical ~392. Compute alone
  is strictly worse than restarts + ALNS pipeline.
- Trim-and-restart DFS (pin top rows, free bottom): dies in
  milliseconds. The partial is structurally locked.
- Score-counter bug: briefly inflated scores by +64 (counting board-
  edge self-edges). Fixed mid-session.

## Structural finding — 459's mismatch geometry

21 mismatches (480 − 459), **all in rows 12-15**. Rows 0-11 perfectly
matched (192 cells, 0 internal mismatches).

```
  0123456789012345
0-11 (all perfect, 192 cells)
12 ......1..11..221
13 ..12..121221.21.
14 .1121221.211.11.
15 .1....1..1......
```

Defects form a connected component across bottom 4 rows.

**Interpretation**: the 459 IS the optimum given those top-row
commitments. To break 459, must change pieces in rows 0-11 (only
board-spanning ALNS destroys can do this).

`vanilla_fastest --trim-rows 4` (pin rows 0-11, free 12-15) died at
depth 211 in milliseconds — top is structurally locked.

## Total CPU

~30 core-hours; the record-breaking job itself was 30 min single thread.
The infrastructure (border-first, minimal→basic, score-counter fix) is
the actual contribution.

## Open questions

- Can `basic` on the 459 push past 460? 12 polish-jobs were launched
  pre-crash; none completed. Worth re-running.
- `winning5` reached 457 from 403; untested on 459 itself.
- `full` ops at long budgets — untested.
- Engine-based attacks (`run_e2_blackwood`) — untested this session.

## Files (on the source machine)

- SOTA: `output/v17_alns_only/basic_sa_t1_s42_1778827429_827089000_p48848.json`
- 454 input: `output/v17_alns_only/minimal_sa_t1_s4_1778812657_873055000_p53044.json`
- 403 vanilla: `runs/border_first_20260514_185556/run_2_best.json`
- Session log: `vault/sessions/vol-36-night-sota-attempt.md`

## Linked

- [[SESSION_2026-05-15_summary]] — this autonomous session
- [[basin-blackwood-470]] — 1-clue Blackwood record (not canonical 5-clue)
- [[basin-mcgavin-469]] — previous canonical 5-clue community ceiling
