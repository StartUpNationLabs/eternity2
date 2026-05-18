// Vol-125 INVENTION — SIGMA-BREAK (bidirectional meet-in-the-middle for BB&B)
//
// Phase 1: forward enumeration of rows 0..R_MID, backward enumeration of
// rows R_MID..7, hash on the (south-edge-profile, piece-set) frontier
// state, and count joinable pairs.
//
// For R_MID = 4, forward enumerates rows 0..=3 (top half), backward rows
// 4..=7 (bottom half). Both enumerate ALL internally-valid super-row
// SEQUENCES with edge matching + piece-uniqueness within the sequence.
//
// Hashing strategy: index forward states by (south_edge_profile_at_row_3,
// piece_bitset). Then for each backward state, look up forward states with
// matching north_edge_profile_at_row_4 (= forward's south at row 3) and
// piece-disjoint bitset.
//
// In practice the piece-set is 256 bits (32 bytes). Hash forward states
// by south-edge tuple (16 bytes) into a HashMap<[(u8,u8); 8], Vec<u256>>.
// At join, for each (back_state, back_north_edge), look up that key and
// for each forward bitset check disjointness.
//
// This is the meet-in-the-middle for the super-block CSP.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8;
const N: usize = 0;
const E: usize = 1;
const S: usize = 2;
const W: usize = 3;
const BORDER: u8 = 0;

#[derive(Debug, Clone, Copy)]
struct Block {
    pieces: [u16; 4],
    rots: [u8; 4],
    edge: [[u8; 2]; 4],
}

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

type BitSet = [u64; 4];
type SouthProfile = [(u8, u8); 8];
type NorthProfile = [(u8, u8); 8];

#[inline]
fn bit_set(bs: &BitSet, p: u16) -> bool {
    (bs[(p as usize) >> 6] >> (p & 63)) & 1 == 1
}
#[inline]
fn bit_or(bs: &mut BitSet, p: u16) {
    bs[(p as usize) >> 6] |= 1u64 << (p & 63);
}
#[inline]
fn bit_and_not(bs: &mut BitSet, p: u16) {
    bs[(p as usize) >> 6] &= !(1u64 << (p & 63));
}
#[inline]
fn bs_disjoint(a: &BitSet, b: &BitSet) -> bool {
    a[0] & b[0] == 0 && a[1] & b[1] == 0 && a[2] & b[2] == 0 && a[3] & b[3] == 0
}

/// Enumerate all valid super-row sequences for the rows `r_start..r_end`,
/// stacking edge-matching, piece-uniqueness across all picked rows.
///
/// The "north constraint" at the top of the first row is fed in. If
/// north_constraint[sc] is Some((c1, c2)), the block at (r_start, sc) must
/// have N-edge = (c1, c2). For sr=0 enumeration, this is all BORDER pairs.
///
/// "border_side" tells us whether east/west must be BORDER at sc=0 and sc=SW-1.
///
/// Visits each found state via the `visit` callback.
fn enumerate_rows(
    alphabets_rows: &[[Vec<Block>; SW]],
    r_start: usize,
    r_end: usize, // exclusive
    initial_north: [Option<(u8, u8)>; SW],
    visit: &mut impl FnMut(&[(u8, u8); SW], &BitSet, &Vec<(usize, usize, usize)>),
) {
    // Enumeration state.
    let nrows = r_end - r_start;
    let mut chosen: Vec<(usize, usize, usize)> = Vec::with_capacity(nrows * SW); // (row_offset, sc, block_idx)
    let mut pieces_used: BitSet = [0; 4];
    // Per-row tracking: the south-edge profile of the current row (after we pick all 8 of its cells).
    let mut north_profile = initial_north;

    fn enum_row(
        row_offset: usize,
        nrows: usize,
        sc: usize,
        e_constraint: Option<(u8, u8)>,
        north_profile: &mut [Option<(u8, u8)>; SW],
        alphabets_rows: &[[Vec<Block>; SW]],
        r_start: usize,
        chosen: &mut Vec<(usize, usize, usize)>,
        pieces_used: &mut BitSet,
        visit: &mut impl FnMut(&[(u8, u8); SW], &BitSet, &Vec<(usize, usize, usize)>),
    ) {
        if sc == SW {
            // Completed this row. Compute the south-edge profile.
            let mut south_profile = [(0u8, 0u8); SW];
            for s in 0..SW {
                let (_, _, bi) = chosen[(chosen.len() - SW) + s];
                let row_actual = r_start + row_offset;
                let b = &alphabets_rows[row_actual][s][bi];
                south_profile[s] = (b.edge[S][0], b.edge[S][1]);
            }
            if row_offset + 1 == nrows {
                // Last row of this enumeration — emit.
                visit(&south_profile, pieces_used, chosen);
            } else {
                // Recurse to next row.
                // Saved old north_profile; new north_profile = current south_profile.
                let mut new_north_profile: [Option<(u8, u8)>; SW] = [None; SW];
                for s in 0..SW { new_north_profile[s] = Some(south_profile[s]); }
                let saved = *north_profile;
                *north_profile = new_north_profile;
                enum_row(
                    row_offset + 1,
                    nrows,
                    0,
                    None,
                    north_profile,
                    alphabets_rows,
                    r_start,
                    chosen,
                    pieces_used,
                    visit,
                );
                *north_profile = saved;
            }
            return;
        }
        let row_actual = r_start + row_offset;
        let alphabet = &alphabets_rows[row_actual][sc];
        for (bi, b) in alphabet.iter().enumerate() {
            // Constraint: N-edge must match.
            if let Some((c1, c2)) = north_profile[sc] {
                if b.edge[N][0] != c1 || b.edge[N][1] != c2 { continue; }
            }
            // Constraint: W-edge.
            if let Some((c1, c2)) = e_constraint {
                if b.edge[W][0] != c1 || b.edge[W][1] != c2 { continue; }
            }
            // Border constraints.
            if sc == 0 && (b.edge[W][0] != BORDER || b.edge[W][1] != BORDER) { continue; }
            if sc == SW - 1 && (b.edge[E][0] != BORDER || b.edge[E][1] != BORDER) { continue; }
            // Piece-uniqueness.
            let mut ok = true;
            for slot in 0..4 {
                if bit_set(pieces_used, b.pieces[slot]) { ok = false; break; }
            }
            if !ok { continue; }
            // Commit.
            for slot in 0..4 { bit_or(pieces_used, b.pieces[slot]); }
            chosen.push((row_offset, sc, bi));
            enum_row(
                row_offset, nrows, sc + 1,
                Some((b.edge[E][0], b.edge[E][1])),
                north_profile, alphabets_rows, r_start,
                chosen, pieces_used, visit,
            );
            chosen.pop();
            for slot in 0..4 { bit_and_not(pieces_used, b.pieces[slot]); }
        }
    }

    enum_row(
        0, nrows, 0, None,
        &mut north_profile,
        alphabets_rows, r_start,
        &mut chosen, &mut pieces_used,
        visit,
    );
}

fn main() {
    let in_dir: PathBuf = "output/vol-125/w14/alphabet".into();
    eprintln!("=== SIGMA-BREAK Phase 1: forward (rows 0..R_MID) enumeration only ===");

    let r_mid: usize = 1; // start small — just row 0
    eprintln!("R_MID = {} (so forward = rows 0..{}, backward = rows {}..8)", r_mid, r_mid, r_mid);

    // Load all super-cell alphabets (just rows 0..r_mid to save memory).
    let t = Instant::now();
    let mut alphabets_rows: [[Vec<Block>; SW]; SW] = Default::default();
    for sr in 0..r_mid {
        for sc in 0..SW {
            let path = in_dir.join(format!("sc_{:02}_{:02}.bin", sr, sc));
            alphabets_rows[sr][sc] = read_blocks(&path);
        }
    }
    eprintln!("Loaded alphabets in {:.1}s", t.elapsed().as_secs_f64());

    // For rows 0..r_mid: north of row 0 is all BORDER.
    let initial_north: [Option<(u8, u8)>; SW] = [Some((BORDER, BORDER)); SW];

    eprintln!("\nEnumerating forward (rows 0..{}, NORTH=BORDER)...", r_mid);
    let t = Instant::now();
    let mut forward_count: u64 = 0;
    let mut south_profile_distinct: HashMap<SouthProfile, u64> = HashMap::new();
    enumerate_rows(
        &alphabets_rows,
        0,
        r_mid,
        initial_north,
        &mut |sp: &SouthProfile, _bs: &BitSet, _chosen: &Vec<(usize, usize, usize)>| {
            forward_count += 1;
            *south_profile_distinct.entry(*sp).or_insert(0) += 1;
            if forward_count % 1_000_000 == 0 {
                eprintln!("  forward state #{}M", forward_count / 1_000_000);
            }
        },
    );
    eprintln!("\nForward enumeration complete:");
    eprintln!("  forward states: {}", forward_count);
    eprintln!("  distinct south-edge profiles: {}", south_profile_distinct.len());
    eprintln!("  elapsed: {:.1}s", t.elapsed().as_secs_f64());

    // Top 10 profiles.
    let mut sorted: Vec<(SouthProfile, u64)> = south_profile_distinct
        .into_iter()
        .map(|(k, v)| (k, v))
        .collect();
    sorted.sort_by_key(|&(_, v)| std::cmp::Reverse(v));
    eprintln!("\nTop 10 south-edge profiles:");
    for (i, (sp, c)) in sorted.iter().take(10).enumerate() {
        eprintln!("  #{}: profile={:?} count={}", i + 1, sp, c);
    }

    let out_path = "/tmp/sigma_break_meet_results.txt";
    let _ = fs::write(
        out_path,
        format!(
            "r_mid={}\nforward_count={}\ndistinct_south_profiles={}\nelapsed={:.3}s\n",
            r_mid, forward_count, sorted.len(), t.elapsed().as_secs_f64()
        ),
    );
    eprintln!("Saved to {}", out_path);
}

// Implement Default for our Block placeholder array.
impl Default for Block {
    fn default() -> Self {
        Block { pieces: [0; 4], rots: [0; 4], edge: [[0; 2]; 4] }
    }
}
