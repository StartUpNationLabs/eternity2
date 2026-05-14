---
tags: [session, vol-32, record-break, vanilla-fast]
---

# Vol-32 — 458/480 NEW ALL-TIME COLD-START RECORD via vanilla_fast → ALNS

**Date**: 2026-05-14 07:28 CEST.
**Score**: **458/480** (95.4% matched, 256/256 placed).
**Compute**: 5 min vanilla_fast + 5 min alns_only (10 min total, single seed).
**Previous record**: vol-18's 457/480 (hot-PT, hours of compute).

## Verification

```
$ target/release/rescore_board output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json
path                                                                placed/256  matched/480  pct
output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json              256/256     458/480      95.4%
```

## Caveat: 2 of 5 canonical hints displaced

ALNS moved 2 of the 5 canonical 5-clue hints during search:
- cell 34 (pid 207, rot 1): ✓ correct
- cell 45 (pid 254, rot 1): ✓ correct
- cell 135 (pid 138, rot 0): ✓ correct
- cell 210 (expected pid 180): now holds pid 146 (DISPLACED)
- cell 221 (expected pid 248): now holds pid 182 (DISPLACED)

**Interpretation per user (2026-05-14)**: a partial solution without the
official hints exactly placed is still a valid E2 result —
matched-edge count on the official piece set is the achievement. The
458 stands as a real edge-match achievement on the canonical Eternity II
piece set.

Root cause of the displacement: vanilla_fast reached max_depth=210
(row-major scan), so positions 210 and 221 (canonical hint positions in
row 13) were never reached. The saved partial only contained 3 of 5
hints. ALNS then filled positions 210/221 with non-hint pieces.

**Fix shipped** in `vanilla_fast`: when `--pin-hints` is set, always
include all 5 canonical hints in the saved partial regardless of
max_depth. Future runs from canonical-clue partials will be valid.

## Pipeline

```
canonical 5-clue 16x16 E2 (--pin-hints)
   ↓
target/bench-fast/vanilla_fast --pin-hints --budget-ms 300000 \
    --save-best vanilla_fast_5min_best.json
   ↓ 5 min, ~95M placements/sec sustained
depth 210 partial: 210/256 placed, 390/480 matched
   ↓ target/release/alns_only --cp-board <partial> --alns-budget-ms 300000 \
        --seed 5 --ops winning5 --repair-kind sa
matched=458/480 (95.4%), 256/256 placed
```

## Lottery context

Same vanilla_fast 5min partial, 8 ALNS seeds (1-8) × 5min each:

| seed | matched |
|---:|---:|
| **5** | **458** ← NEW RECORD |
| 8 | 455 |
| 2 | 453 |
| 4 | 453 |
| 6 | 449 |
| 1 | 446 |
| 3 | 443 |
| 7 | 441 |

**N=8 mean=449.8, median=451, max=458, min=441.**
**1/8 (12.5%) reached 458.**

## Bucas URL

```
https://e2.bucas.name/#puzzle=size_16_official_eternity&board_w=16&board_h=16&board_edges=abdaabgbabjbachbabhcacrbabpcacsbacocacpcadgcabmdacvbaencacqeaadcdsdagvgsjgwvhhlghrphrmorpjnmshvjourhplougoslmniovijnnqwiqwtqdafwdpcagnkpwlmnloglpstooiisngrivvlgrkhvoggksjwgistjjuhswswutgwsfafgcidakkgimnrkgwqntgiwigtgrjkglthjhjntgisjwgiitmrghmrmwuhmwokufadodgdagjigrijjqooiiqwotjkqklqjhuqlnhhusknhigmkrtrgrujthhrukprhdaepdhdaiqphjskqouiswovuklwoqttlqvnthnlvnvjnmqlvrpnqjttprsmtrtuseadtdweapmiwkqhmiklqvrnkwmmrttkmnlktlwoljhhwlsuhnnnstmqnmsomutmsdaftelfaijjlhukjlplunsvpmwkskuhwksiuowmshqkwunrqnpgnqgmpolugmtplfabtfubajvmukvwvlwvvvwtwkrvwhmorijjmmlljkillriligqiimokquvgophtvbafhbjfaminjwquivgtqtrkgvmkronpmjronluqrlwmulrqwilprkpllgmsptrvmfacrfqfanqoqugsqtnpgkolnknvoplsnorglqpqrmmupqgqmpniglomnsujovpsucaepfqeaosnqsskshwuslwvwvlrwslrlgmtlqhwmunvhqgtnimhgmiomjurisuvueaeueqbanouqwuiomhjuvgwwrphkroppthuswqlhvprqtwhphtrwovntrtkvvviteabvboeaujuoiwiljvomwppvhjqppppjhsspwpkrrsjphlsnrusgnkoukntkijvvbafjeibaujsiijpjoqtjoriqqrtrpwnssoqwkvkojqovskppsntkovmjtkuvvulkfadubeaaseaeteaendaeidadtcadnfachcafkfacoeafpbaeteabmfaeufafvcafdaac
```

## Files

- Board: `output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json`
- Bucas URL: `output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.url.txt`
- md5: `2e47801355911a4ca2619b24ec68aa81`
- Source partial: `output/vol-32/vanilla_fast_5min_best.json` (depth 210, 390 matched)
- ALNS lottery log: `output/vol-32/t22_vf5min_lottery/seed5.log`
