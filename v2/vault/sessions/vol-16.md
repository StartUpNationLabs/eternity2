# Session — vol-16

**Theme**: Cleanup volume. 4.6× engine speedup. Cat-2 PropagatorConfig extraction. score_board O(n²)→O(n).
**Raw**: [[archive/raw/RESEARCH_NOTES_16|RESEARCH_NOTES_16.md]], [[archive/raw/OPTIMIZATION_REPORT|OPTIMIZATION_REPORT.md]]

## What was attempted

- Profile-driven cleanup of 8 debt categories from the [[mcgavin-engine|McGavin gap]] motivated by vol-15's 47× BLACKWOOD_RAW finding.
- Arena-based undo (vs `Vec<Undo>` per entry).
- `PropagatorConfig` sub-struct extraction (Cat-2).
- `score_board` algorithmic rewrite (O(n²) → O(n) via `Puzzle::piece` O(1) cache).
- Precomputed `same_piece_rots` LUT for AC-3.
- `bench-audit` crate: −652 lines deduplication.

## What was measured / kept

- **BLACKWOOD_RAW: ~80k → ~367k nps single-thread (4.6×)**.
- **`joe_depth150_par`: ~2.4k → ~7k nps (2.9×)**. Headline algorithmic win: precomputed `same_piece_rots` LUT.
- **score_board** O(n²) → O(n) via `Puzzle::piece` O(1) cache.
- `PropagatorConfig` sub-struct (clean Cat-2 cleanup).
- 21 commits shipped.

## What was refuted

- **class_balance propagator** in `BLACKWOOD_RAW`: dropped, 2.4× win.
- **Cat-2 stage A regex bug**: silently failed 17/30 profile slabs. Fixed.

## Concepts touched

- [[bitset-domain-rep]] (LUT addition)
- [[engine-profile-registry]] (Cat-2 cleanup of PropagatorConfig)
- [[ac3]] (`same_piece_rots` LUT win)

## Insight

Cleanup volume produced **larger speedup than vol-12 bitset rewrite** by addressing allocator pressure + dedup. We still have ~800× to go to match McGavin (~367k vs 295M nps), but the path is concrete.

## Linked memory

- `project_e2_vol16_cleanup_anchor` (8-category playbook)
- `project_e2_vol16_closeout` (results)
