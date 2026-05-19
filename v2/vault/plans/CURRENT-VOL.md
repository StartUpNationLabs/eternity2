# Current Volume — Vol-151

**Theme**: WEAVING-Beam — beam-search variant of the V150 constructive
builder. Trades random-seed-sweep for structured top-K-at-each-depth
exploration.

V150 random sweep → max 408 at 50k seeds. Log-N growth predicts
~440 needs 10⁹ seeds (~16 days). Beam search aims to cut that cost.

## Binding items (3 max)

1. **Math** in [[../concepts/weaving-beam]] (done).
2. **Rust impl** at `crates/bench-audit/src/bin/v151_weaving_beam.rs`.
   Beam width K configurable. Used-mask diversity dedup.
3. **Measure** K ∈ {1, 16, 64, 256, 1024, 4096} × {row, col} × 3 seeds
   each (variance reporting). Report max, median, time-per-K.

## Kill-criteria

- K=64 doesn't beat V150 random-sweep max (408) → beam doesn't help.
- K=1024 doesn't reach ≥420 → diminishing returns; refute scale.
- Memory exhaustion at K=4096 → cap K; report the practical ceiling.

## Days budget

2 days. Day-1: implement + small-K test. Day-2: large-K + variance
reporting + close.

## Linked

- [[../sessions/vol-151]] (to create)
- [[../concepts/weaving-beam]] (created)
- [[../sessions/vol-150]] (parent)
- [[INVENTION_NAMES_2026-05-19]]
