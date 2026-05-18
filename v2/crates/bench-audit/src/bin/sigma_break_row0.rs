// Vol-125 INVENTION — SIGMA-BREAK (bidirectional meet-in-the-middle for BB&B)
//
// Phase 0: enumerate ALL internally-valid row-0 super-block sequences for
// canonical Eternity II's W14 alphabet. A row-0 sequence is an 8-tuple of
// super-blocks at (0, 0), (0, 1), ..., (0, 7) where:
//   - block at (0, sc) has west-edge matching east-edge of block at (0, sc-1)
//   - block at (0, 0) has west-edge = (BORDER, BORDER)
//   - block at (0, 7) has east-edge = (BORDER, BORDER)
//   - pieces used within the row are all distinct (32 distinct pieces)
//   - block at (0, sc) has north-edge = (BORDER, BORDER) (already enforced
//     by W14 alphabet for sr=0)
//
// Output: a count + sample of valid row-0 sequences, plus a signature
// histogram of south-edge profiles.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8;

#[derive(Debug, Clone, Copy)]
struct Block {
    pieces: [u16; 4],
    rots: [u8; 4],
    edge: [[u8; 2]; 4],
}
const N: usize = 0;
const E: usize = 1;
const S: usize = 2;
const W: usize = 3;

const BORDER: u8 = 0; // Canonical Eternity II border color = 0 (eternity2-core::BORDER)

fn read_blocks(path: &PathBuf) -> Vec<Block> {
    let bytes = fs::read(path).expect("read alphabet file");
    assert_eq!(&bytes[..4], b"W14B");
    let n = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    let mut blocks = Vec::with_capacity(n);
    let mut off = 8;
    for _ in 0..n {
        let mut b = Block { pieces: [0; 4], rots: [0; 4], edge: [[0; 2]; 4] };
        for j in 0..4 {
            b.pieces[j] = u16::from_le_bytes([bytes[off + 2 * j], bytes[off + 2 * j + 1]]);
        }
        off += 8;
        for j in 0..4 { b.rots[j] = bytes[off + j]; }
        off += 4;
        for s in 0..4 {
            b.edge[s].copy_from_slice(&bytes[off..off + 2]);
            off += 2;
        }
        blocks.push(b);
    }
    blocks
}

fn main() {
    let in_dir: PathBuf = "output/vol-125/w14/alphabet".into();
    eprintln!("=== SIGMA-BREAK Phase 0: enumerate row-0 super-block sequences ===");

    // Load all 8 cells of row 0.
    let t = Instant::now();
    let mut row0_alphabets: Vec<Vec<Block>> = Vec::with_capacity(SW);
    for sc in 0..SW {
        let path = in_dir.join(format!("sc_{:02}_{:02}.bin", 0, sc));
        let blocks = read_blocks(&path);
        eprintln!("  (0,{}): {} blocks", sc, blocks.len());
        row0_alphabets.push(blocks);
    }
    eprintln!("Loaded row-0 alphabets in {:.1}s", t.elapsed().as_secs_f64());

    // Pre-filter for cell-specific constraints:
    //   - all cells: N = (BORDER, BORDER) (should already be enforced by W14 enumerator)
    //   - cell (0, 0): also W = (BORDER, BORDER)
    //   - cell (0, 7): also E = (BORDER, BORDER)
    let t = Instant::now();
    let filtered: Vec<Vec<usize>> = (0..SW).map(|sc| {
        row0_alphabets[sc].iter().enumerate().filter_map(|(i, b)| {
            if b.edge[N][0] != BORDER || b.edge[N][1] != BORDER { return None; }
            if sc == 0 && (b.edge[W][0] != BORDER || b.edge[W][1] != BORDER) { return None; }
            if sc == SW - 1 && (b.edge[E][0] != BORDER || b.edge[E][1] != BORDER) { return None; }
            Some(i)
        }).collect()
    }).collect();
    for sc in 0..SW {
        eprintln!("  (0,{}): {} blocks after border filter", sc, filtered[sc].len());
    }
    eprintln!("Border-filter pass in {:.1}s", t.elapsed().as_secs_f64());

    // Now enumerate row-0 sequences with edge matching + intra-row piece uniqueness.
    // Track south-edge profile (8 super-edges, each a (u8, u8) pair) for the
    // signature histogram.
    let t = Instant::now();
    let mut count: u64 = 0;
    let mut south_profile_counts: HashMap<[(u8, u8); 8], u64> = HashMap::new();
    let mut chosen: Vec<usize> = vec![0; SW];
    let mut pieces_used = vec![false; 256];

    fn enumerate(
        sc: usize,
        e_constraint: Option<[u8; 2]>,
        row0_alphabets: &[Vec<Block>],
        filtered: &[Vec<usize>],
        chosen: &mut [usize],
        pieces_used: &mut [bool],
        count: &mut u64,
        south_profile_counts: &mut HashMap<[(u8, u8); 8], u64>,
        cap: u64,
    ) {
        if sc == SW {
            *count += 1;
            // Compute south-edge profile.
            let mut profile = [(0u8, 0u8); 8];
            for s in 0..SW {
                let b = &row0_alphabets[s][chosen[s]];
                profile[s] = (b.edge[S][0], b.edge[S][1]);
            }
            *south_profile_counts.entry(profile).or_insert(0) += 1;
            return;
        }
        for &cand_idx in &filtered[sc] {
            let b = &row0_alphabets[sc][cand_idx];
            // Check W-edge match.
            if let Some(e_c) = e_constraint {
                if b.edge[W] != e_c { continue; }
            }
            // Check piece-uniqueness.
            let mut ok = true;
            for slot in 0..4 {
                if pieces_used[b.pieces[slot] as usize] { ok = false; break; }
            }
            if !ok { continue; }
            // Commit.
            for slot in 0..4 { pieces_used[b.pieces[slot] as usize] = true; }
            chosen[sc] = cand_idx;
            enumerate(
                sc + 1,
                Some(b.edge[E]),
                row0_alphabets,
                filtered,
                chosen,
                pieces_used,
                count,
                south_profile_counts,
                cap,
            );
            // Uncommit.
            for slot in 0..4 { pieces_used[b.pieces[slot] as usize] = false; }
            if *count >= cap { return; }
        }
    }

    let cap: u64 = 100_000_000_000;
    enumerate(
        0,
        None,
        &row0_alphabets,
        &filtered,
        &mut chosen,
        &mut pieces_used,
        &mut count,
        &mut south_profile_counts,
        cap,
    );

    eprintln!("\n=== Results ===");
    eprintln!("Row-0 internally-valid sequences: {}", count);
    eprintln!("Distinct south-edge profiles: {}", south_profile_counts.len());
    eprintln!("Enumeration time: {:.1}s", t.elapsed().as_secs_f64());

    // Most common profiles.
    let mut sorted_profiles: Vec<(_, u64)> = south_profile_counts.iter()
        .map(|(k, v)| (k.clone(), *v))
        .collect();
    sorted_profiles.sort_by_key(|&(_, v)| std::cmp::Reverse(v));
    eprintln!("Top 10 south-edge profiles by count:");
    for (i, (profile, c)) in sorted_profiles.iter().take(10).enumerate() {
        eprintln!("  #{}: profile={:?} count={}", i + 1, profile, c);
    }

    // Save summary.
    let out_path = "/tmp/sigma_break_row0_count.txt";
    let _ = fs::write(
        out_path,
        format!(
            "count={}\ndistinct_south_profiles={}\nelapsed={:.3}s\n",
            count, south_profile_counts.len(), t.elapsed().as_secs_f64()
        ),
    );
    eprintln!("Saved to {}", out_path);
}
