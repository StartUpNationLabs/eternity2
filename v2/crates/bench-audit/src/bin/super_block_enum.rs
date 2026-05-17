// W14 super-block enumerator (Rust port of scripts/w15_qubo/w14_super_block_attack.py).
//
// Enumerates all internally-matched 2x2 piece blocks for canonical Eternity II.
// Each super-cell at (sr, sc) in an 8x8 super-grid covers 4 cells. A "block"
// is a 4-tuple of (piece, rotation) placements at TL, TR, BL, BR of the super-
// cell such that internal edges match. Outside edges of the block become the
// super-cell's N/E/S/W boundary (each a pair of colors).
//
// Output: writes per-super-cell alphabets to disk as binary files for later
// loading by the AC-3 propagator and SAT encoder.
//
// Usage:
//   super_block_enum [--puzzle path] [--out-dir output/w14] [--position interior|tl|...]

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Piece, Puzzle, Rotation, BORDER};
use std::collections::HashMap;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

const W: usize = 16;
const SW: usize = 8;

#[derive(Debug, Clone, Copy)]
struct PieceRot {
    pid: u16,
    rot: u8,
    edges: [u8; 4], // N, E, S, W after rotation
}

#[derive(Debug, Clone, Copy)]
struct Block {
    pieces: [u16; 4], // TL, TR, BL, BR piece ids
    rots: [u8; 4],    // TL, TR, BL, BR rotations
    n_edge: [u8; 2],  // (TL.N, TR.N)
    e_edge: [u8; 2],  // (TR.E, BR.E)
    s_edge: [u8; 2],  // (BL.S, BR.S)
    w_edge: [u8; 2],  // (TL.W, BL.W)
}

fn all_piece_rots(puzzle: &Puzzle) -> Vec<PieceRot> {
    let mut out = Vec::with_capacity(puzzle.pieces().len() * 4);
    for piece in puzzle.pieces() {
        for r in 0..4u8 {
            let rot = match r {
                0 => Rotation::R0,
                1 => Rotation::R90,
                2 => Rotation::R180,
                _ => Rotation::R270,
            };
            let e = piece.edges.rotated(rot).as_array();
            out.push(PieceRot { pid: piece.id, rot: r, edges: e });
        }
    }
    out
}

fn position_class(sr: usize, sc: usize) -> [[bool; 4]; 4] {
    // For each slot (TL=0, TR=1, BL=2, BR=3), which sides must be BORDER?
    // sides: N=0, E=1, S=2, W=3
    let mut must_border = [[false; 4]; 4]; // [slot][side]
    if sr == 0 {
        must_border[0][0] = true; // TL.N
        must_border[1][0] = true; // TR.N
    }
    if sr == SW - 1 {
        must_border[2][2] = true; // BL.S
        must_border[3][2] = true; // BR.S
    }
    if sc == 0 {
        must_border[0][3] = true; // TL.W
        must_border[2][3] = true; // BL.W
    }
    if sc == SW - 1 {
        must_border[1][1] = true; // TR.E
        must_border[3][1] = true; // BR.E
    }
    must_border
}

fn slot_candidates(
    all_rots: &[PieceRot],
    must_border: &[bool; 4],
    pinned_pid: Option<u16>,
    pinned_rot: Option<u8>,
) -> Vec<PieceRot> {
    let mut out = Vec::new();
    for pr in all_rots {
        if let Some(pid) = pinned_pid {
            if pr.pid != pid { continue; }
        }
        if let Some(rot) = pinned_rot {
            if pr.rot != rot { continue; }
        }
        let mut ok = true;
        for side in 0..4 {
            let is_border = pr.edges[side] == BORDER;
            if must_border[side] && !is_border { ok = false; break; }
            if !must_border[side] && is_border { ok = false; break; }
        }
        if ok { out.push(*pr); }
    }
    out
}

fn enumerate_supercell(
    all_rots: &[PieceRot],
    sr: usize,
    sc: usize,
    pinned: Option<(u8, u16, u8)>, // (slot, pid, rot)
) -> Vec<Block> {
    let must_border = position_class(sr, sc);

    let mk = |slot: usize| -> Vec<PieceRot> {
        let (pid, rot) = match pinned {
            Some((s, pid, rot)) if s as usize == slot => (Some(pid), Some(rot)),
            _ => (None, None),
        };
        slot_candidates(all_rots, &must_border[slot], pid, rot)
    };

    let tl = mk(0);
    let tr = mk(1);
    let bl = mk(2);
    let br = mk(3);

    // Index TL by E, TR by W, BL by N, BR by (N, W)
    let mut tl_by_e: HashMap<u8, Vec<PieceRot>> = HashMap::new();
    for p in &tl { tl_by_e.entry(p.edges[1]).or_default().push(*p); }
    let mut tr_by_w: HashMap<u8, Vec<PieceRot>> = HashMap::new();
    for p in &tr { tr_by_w.entry(p.edges[3]).or_default().push(*p); }
    let mut bl_by_n: HashMap<u8, Vec<PieceRot>> = HashMap::new();
    for p in &bl { bl_by_n.entry(p.edges[0]).or_default().push(*p); }
    let mut br_by_nw: HashMap<(u8, u8), Vec<PieceRot>> = HashMap::new();
    for p in &br { br_by_nw.entry((p.edges[0], p.edges[3])).or_default().push(*p); }

    let mut blocks = Vec::new();
    for (&c_lr, tls) in tl_by_e.iter() {
        let trs = match tr_by_w.get(&c_lr) {
            Some(v) => v,
            None => continue,
        };
        for &tl_p in tls {
            for &tr_p in trs {
                if tr_p.pid == tl_p.pid { continue; }
                // BL.N must = TL.S
                let bls = match bl_by_n.get(&tl_p.edges[2]) {
                    Some(v) => v,
                    None => continue,
                };
                for &bl_p in bls {
                    if bl_p.pid == tl_p.pid || bl_p.pid == tr_p.pid { continue; }
                    // BR.N = TR.S, BR.W = BL.E
                    let key = (tr_p.edges[2], bl_p.edges[1]);
                    let brs = match br_by_nw.get(&key) {
                        Some(v) => v,
                        None => continue,
                    };
                    for &br_p in brs {
                        if br_p.pid == tl_p.pid || br_p.pid == tr_p.pid || br_p.pid == bl_p.pid {
                            continue;
                        }
                        blocks.push(Block {
                            pieces: [tl_p.pid, tr_p.pid, bl_p.pid, br_p.pid],
                            rots:   [tl_p.rot, tr_p.rot, bl_p.rot, br_p.rot],
                            n_edge: [tl_p.edges[0], tr_p.edges[0]],
                            e_edge: [tr_p.edges[1], br_p.edges[1]],
                            s_edge: [bl_p.edges[2], br_p.edges[2]],
                            w_edge: [tl_p.edges[3], bl_p.edges[3]],
                        });
                    }
                }
            }
        }
    }
    blocks
}

fn write_blocks_binary(blocks: &[Block], path: &PathBuf) -> std::io::Result<()> {
    let mut f = std::io::BufWriter::new(fs::File::create(path)?);
    // Magic + length
    f.write_all(b"W14B")?;
    f.write_all(&(blocks.len() as u32).to_le_bytes())?;
    for b in blocks {
        for p in &b.pieces { f.write_all(&p.to_le_bytes())?; }
        f.write_all(&b.rots)?;
        f.write_all(&b.n_edge)?;
        f.write_all(&b.e_edge)?;
        f.write_all(&b.s_edge)?;
        f.write_all(&b.w_edge)?;
    }
    f.flush()
}

fn main() {
    let mut puzzle_path: PathBuf = "../data/puzzles/size_16_official_eternity.csv".into();
    let mut out_dir: PathBuf = "output/w14/alphabet".into();
    let mut do_write = true;

    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = args[i + 1].clone().into(); i += 2; }
            "--out-dir" => { out_dir = args[i + 1].clone().into(); i += 2; }
            "--no-write" => { do_write = false; i += 1; }
            _ => { eprintln!("Unknown arg: {}", args[i]); std::process::exit(2); }
        }
    }

    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!(
        "Puzzle: {}x{}, {} pieces, {} colors",
        puzzle.width, puzzle.height, puzzle.pieces().len(), puzzle.color_count - 1
    );
    let all_rots = all_piece_rots(&puzzle);

    // Canonical hints
    let hints: HashMap<(usize, usize), (u8, u16, u8)> = HashMap::from([
        // Hint at flat-pos 135 = (row 8, col 7) → super-cell (4, 3) slot TR
        ((4usize, 3usize), (1u8, 138u16, 0u8)),
        // Pos 210 = (row 13, col 2) → (6, 1) slot BL
        ((6, 1), (2u8, 180u16, 1u8)),
        // Pos 34 = (row 2, col 2) → (1, 1) slot TL
        ((1, 1), (0u8, 207u16, 1u8)),
        // Pos 221 = (row 13, col 13) → (6, 6) slot BR
        ((6, 6), (3u8, 248u16, 2u8)),
        // Pos 45 = (row 2, col 13) → (1, 6) slot TR
        ((1, 6), (1u8, 254u16, 1u8)),
    ]);

    if do_write {
        fs::create_dir_all(&out_dir).expect("create out dir");
    }

    let t0 = Instant::now();
    let mut total = 0u64;
    let mut per_sc = Vec::new();
    for sr in 0..SW {
        for sc in 0..SW {
            let t_sc = Instant::now();
            let pinned = hints.get(&(sr, sc)).copied();
            let blocks = enumerate_supercell(&all_rots, sr, sc, pinned);
            total += blocks.len() as u64;
            let elapsed = t_sc.elapsed();
            let tag = if pinned.is_some() { " HINT" } else { "" };
            eprintln!(
                "  ({sr},{sc}) {:>10} blocks{} ({:.2}s)",
                blocks.len(), tag, elapsed.as_secs_f64()
            );
            per_sc.push(((sr, sc), blocks.len()));
            if do_write {
                let path = out_dir.join(format!("sc_{:02}_{:02}.bin", sr, sc));
                write_blocks_binary(&blocks, &path).expect("write blocks");
            }
        }
    }
    eprintln!(
        "\nTotal alphabet: {} blocks in {:.1}s",
        total, t0.elapsed().as_secs_f64()
    );
    if do_write { eprintln!("Wrote per-supercell alphabets to {}", out_dir.display()); }
}
