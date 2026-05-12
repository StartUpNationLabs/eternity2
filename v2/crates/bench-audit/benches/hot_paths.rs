// Criterion benches for the audit candidates.
//
// Run with:
//   cargo bench -p eternity2-bench-audit
//   cargo bench -p eternity2-bench-audit --bench hot_paths -- rotate
//   cargo bench -p eternity2-bench-audit --bench hot_paths -- score
//
// Each group compares a *baseline* (current engine code) with a *candidate*
// (proposal in the audit). The baseline is materialised here so the
// comparison is honest even if the engine changes later.

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};

use eternity2_bench_audit::{
    build_edges_grid, build_propagator_inputs, build_puzzle, pack_board,
    rotate_edges_baseline, rotate_edges_packed, run_gacolor, run_parity,
    score_board_baseline_wrapper, score_packed, solved_board,
};
use eternity2_core::{Color, Position};

fn bench_rotate(c: &mut Criterion) {
    let mut group = c.benchmark_group("rotate_edges");
    // Use a fixed batch of 256 representative tuples so we measure the
    // inner loop, not the call dispatch.
    let mut samples: Vec<[Color; 4]> = Vec::with_capacity(256);
    for i in 0..256u32 {
        samples.push([
            (i & 0x0F) as Color,
            ((i >> 4) & 0x0F) as Color,
            ((i >> 8) & 0x0F) as Color,
            ((i >> 12) & 0x0F) as Color,
        ]);
    }
    group.bench_function("baseline_array_match", |b| {
        b.iter(|| {
            let mut acc: u32 = 0;
            for &e in &samples {
                for r in 0..4u8 {
                    let out = rotate_edges_baseline(e, r);
                    acc = acc.wrapping_add(out[0] as u32);
                }
            }
            black_box(acc)
        });
    });
    group.bench_function("candidate_packed_u32_rotate", |b| {
        b.iter(|| {
            let mut acc: u32 = 0;
            for &e in &samples {
                for r in 0..4u8 {
                    let out = rotate_edges_packed(e, r);
                    acc = acc.wrapping_add(out[0] as u32);
                }
            }
            black_box(acc)
        });
    });
    group.finish();
}

fn bench_score(c: &mut Criterion) {
    let mut group = c.benchmark_group("score_board");
    for &size in &[6u32, 10, 14] {
        let puzzle = build_puzzle(size, 5, 0xC0FFEE);
        let board = solved_board(&puzzle);
        let grid = build_edges_grid(&puzzle, &board);
        group.bench_with_input(BenchmarkId::new("baseline_localsearch", size), &size, |b, _| {
            b.iter(|| black_box(score_board_baseline_wrapper(&puzzle, &board)));
        });
        group.bench_with_input(BenchmarkId::new("candidate_dense_edges_grid", size), &size, |b, _| {
            b.iter(|| black_box(score_packed(&puzzle, &grid)));
        });
    }
    group.finish();
}

fn bench_propagators(c: &mut Criterion) {
    let mut group = c.benchmark_group("propagators");
    for &size in &[6u32, 10, 14] {
        let puzzle = build_puzzle(size, 5, 0xBEEF);
        // Build a half-placed board: top half placed, bottom half open.
        let mut board = solved_board(&puzzle);
        for pos in (puzzle.cell_count() / 2)..puzzle.cell_count() {
            board = {
                let mut b = board.clone();
                b.clear(pos as Position);
                b
            };
        }
        let (placed, used, domain_bits, wpp) = build_propagator_inputs(&puzzle, &board);
        group.bench_with_input(BenchmarkId::new("gacolor_check", size), &size, |b, _| {
            b.iter(|| run_gacolor(&puzzle, &placed, &used, &domain_bits, wpp));
        });
        group.bench_with_input(BenchmarkId::new("parity_check", size), &size, |b, _| {
            b.iter(|| run_parity(&puzzle, &placed, &used, &domain_bits, wpp));
        });
    }
    group.finish();
}

fn bench_board_get(c: &mut Criterion) {
    let mut group = c.benchmark_group("board_get");
    let puzzle = build_puzzle(14, 5, 0xCAFE);
    let board = solved_board(&puzzle);
    let packed = pack_board(&puzzle, &board);
    group.bench_function("baseline_option_tuple", |b| {
        b.iter(|| {
            let mut acc: u32 = 0;
            for pos in 0..puzzle.cell_count() {
                if let Some((pid, rot)) = board.get(pos) {
                    acc = acc.wrapping_add(pid as u32).wrapping_add(rot.as_u8() as u32);
                }
            }
            black_box(acc)
        });
    });
    group.bench_function("candidate_packed_u32", |b| {
        b.iter(|| {
            let mut acc: u32 = 0;
            for pos in 0..puzzle.cell_count() {
                if let Some((pid, rot)) = packed.get(pos) {
                    acc = acc.wrapping_add(pid as u32).wrapping_add(rot.as_u8() as u32);
                }
            }
            black_box(acc)
        });
    });
    group.finish();
}

criterion_group!(audit, bench_rotate, bench_score, bench_propagators, bench_board_get);
criterion_main!(audit);
