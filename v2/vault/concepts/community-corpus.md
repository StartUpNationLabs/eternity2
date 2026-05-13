---
tags: [concept, reference, infrastructure]
status: built
origin-vol: 8
---

# Community export corpus

**Status**: `built` (vol-8)
**Origin**: vol-8
**Files**: `scripts/community_build_corpus.py`, `community_export_grep.sh`, `community_extract_bucas.py`

## Sources

- `v2/community-exports/messages.jsonl` — **11,511** groups.io messages, 2000-10-22 → 2026-01.
- `v2/community-exports/eternity2-discord-general.csv` — **1,198** Discord messages, 2021-11-23 → 2026-01-24.

## Built outputs

- `output/v8_grep/corpus.txt` — 27.6 MB flat corpus, every line prefixed `[<source>:<id>|<date>|<author>|<subject>] body`.
- `output/v8_grep/hits/*.txt` — per-pattern hit files (50-pattern mining battery).
- `output/community_corpus/_index.tsv` — **123 decoded bucas boards**, ranked by score.
- `output/community_corpus/groups_*.json` + `discord_*.json` — the actual boards.

## Verified community ceiling (vol-8 + memory `reference_community_e2_ceiling`)

**Canonical 5-clue Monckton E2: 469/480** by Peter McGavin (2020-09-09), groups.io message 172011298. All 256 pieces in IDs 1..256. Achieved by running Joshua Blackwood's solver on ~200 cores for "a few days".

Confounds rejected:
- McGavin's "480" (2023-10-09) uses mixed Clue1+Clue2 piece sets (board_pieces > 256). Not canonical.
- McGavin's 471 / Razvan 480 on Joe's 17-color and Brendan's 16×16 variants.
- Blackwood's 470 on 0-clue / unframed variant (see [[reference-blackwood-decoded]]).
- Takahashi's 468 (chokudai 2009) on TopCoder unframed variant.

## Notable authors

- **Louis Verhaard** — `eii` solver author, 467 in 2008 ([[verhaard-set-sa]])
- **Peter McGavin** — most prolific 2017-2026, 469 in 2020
- **Joshua Blackwood** (`jblackwood345`) — C# solver, 470 on Blackwood-variant ([[blackwood-algorithm]])
- **Jef Bucas** — `e2.bucas.name` visualiser + `libblackwood` author ([[mcgavin-engine]])
- **anr_56** — 2007 Eulerian-cycle border theorist ([[eulerian-border]])
- **Al Hopfer** — stall-point + piece-budget observations 2021; NS-1 invariant ([[ns1-deficit]])
- **Mike Pringle / Joe** — 2026-01 thread on Joe's pruning policy ([[prune-restart]])
- **onesmallstep** — Discord admin, active 2024-2026; piece 17/38/62 insights
- **reinout_** — Rust solver based on Blackwood, at 469 chasing 470
- **guenter stertenbrink** — Eternity I survivor, deep technical

## Query recipes

```bash
# all canonical-E2 boards
awk -F'\t' '$3 == "Eternity2"' output/community_corpus/_index.tsv

# every 5-clue claim ≥ 460/480
grep -E '\b(46[0-9]|47[0-9])/480\b' output/v8_grep/corpus.txt

# all posts by an author
grep -F '|Peter McGavin|' output/v8_grep/corpus.txt | head

# pull a specific groups.io thread
awk '/\[groups:172011298\|/' output/v8_grep/corpus.txt
```

## How to apply

When researching E2, this corpus is the canonical non-paywalled archive of community knowledge. Search here before dispatching agents to scrape forums (vol-7 found groups.io paywalled to scrapers; this export bypasses that limitation entirely).

## Linked concepts

- [[blackwood-algorithm]] — algorithm decoded from this corpus
- [[verhaard-set-sa]] — algorithm decoded from this corpus
- [[mcgavin-engine]] — throughput target identified here
- [[prune-restart]] — Joe's policy identified here
- [[eulerian-border]] — anr_56 method, refuted on canonical E2

## Linked memory

- `reference_e2_community_corpus`
- `reference_community_e2_ceiling`
- `reference_blackwood_decoded`
- `reference_verhaard_actual_method`
