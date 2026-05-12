// Sample feasible E2 border arrangements via Las Vegas backtracking.
//
// All 5 official hint pieces are INTERIOR — the border (60 cells) has
// no hint constraints. The border CSP is large: per-side single chain
// with start/end colors fixed has 10⁶+ feasible paths, and the full
// 60-deep enumeration is intractable.
//
// RESEARCH_NOTES_6 BORDER-2 sampling diagnostic showed: top-side from
// color 1 to color 2 has 5.77M+ paths in 30s of Python (cut off, not
// exhausted). Total border space is ≥10²² before piece-disjoint
// constraints. The 3-border corpus monoculture is purely algorithmic
// stickiness, not a property of the border space.
//
// Algorithm (Las Vegas sampling):
//   1. Pick a (TL, TR, BR, BL) corner-quad uniformly at random from
//      the ~24 distinct quadruples.
//   2. For each side independently: randomized backtracking to find
//      ONE feasible 14-piece path with the right start/end colors.
//      Use random rotation of candidate order at each step. If dead
//      end: backtrack normally. If still no path after N attempts:
//      re-sample corner quad.
//   3. Cross-side piece-disjoint check. If fails, retry from step 1.
//   4. Repeat until N borders found.
//
// This is dramatically simpler and much faster than enumeration.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Piece, PieceId, Rotation, BORDER};

#[derive(Parser, Debug)]
#[command(name = "border_enumerate", about = "Sample feasible E2 border arrangements")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Stop after this many distinct borders found.
    #[arg(long, default_value_t = 1000)]
    n_target: usize,

    /// Wall-clock budget in seconds.
    #[arg(long, default_value_t = 300)]
    time_budget: u64,

    /// Output path (JSONL: one border per line).
    #[arg(long, default_value = "output/borders/border_library.jsonl")]
    out: PathBuf,

    /// Periodic progress every N samples.
    #[arg(long, default_value_t = 1000)]
    log_every: u64,

    /// RNG seed.
    #[arg(long, default_value_t = 0xCAFEBABE_DEADBEEFu64)]
    seed: u64,

    /// Per-side backtrack node budget (attempts to find ONE valid path).
    #[arg(long, default_value_t = 100_000)]
    side_node_budget: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Side { Top, Right, Bottom, Left }

#[derive(Clone, Copy, Debug)]
enum CornerKind { TL, TR, BR, BL }

#[derive(Clone, Copy, Debug)]
struct CornerPlacement {
    pid: PieceId,
    rot: u8,
    outgoing: u8,
    incoming: u8,
}

fn corner_placements(pieces: &[Piece], kind: CornerKind) -> Vec<CornerPlacement> {
    let mut out = Vec::new();
    for p in pieces {
        if !p.is_corner() { continue; }
        for r in 0..4u8 {
            let rot = Rotation::from_u8(r).unwrap();
            let e = p.edges.rotated(rot);
            let (t, ri, b, le) = (e.top(), e.right(), e.bottom(), e.left());
            let placement = match kind {
                CornerKind::TL => if t == BORDER && le == BORDER { Some(CornerPlacement { pid: p.id, rot: r, outgoing: ri, incoming: b }) } else { None },
                CornerKind::TR => if t == BORDER && ri == BORDER { Some(CornerPlacement { pid: p.id, rot: r, outgoing: b,  incoming: le }) } else { None },
                CornerKind::BR => if b == BORDER && ri == BORDER { Some(CornerPlacement { pid: p.id, rot: r, outgoing: le, incoming: t }) } else { None },
                CornerKind::BL => if b == BORDER && le == BORDER { Some(CornerPlacement { pid: p.id, rot: r, outgoing: t,  incoming: ri }) } else { None },
            };
            if let Some(p) = placement { out.push(p); }
        }
    }
    out
}

#[derive(Clone, Copy, Debug)]
#[allow(dead_code)]
struct EdgePlacement {
    pid: PieceId,
    rot: u8,
    prev_color: u8,
    next_color: u8,
    inward: u8,
}

fn edge_placements(pieces: &[Piece], side: Side) -> Vec<EdgePlacement> {
    let mut out = Vec::new();
    for p in pieces {
        if !p.is_edge() { continue; }
        for r in 0..4u8 {
            let rot = Rotation::from_u8(r).unwrap();
            let e = p.edges.rotated(rot);
            let (t, ri, b, le) = (e.top(), e.right(), e.bottom(), e.left());
            let placement = match side {
                Side::Top    => if t == BORDER  { Some(EdgePlacement { pid: p.id, rot: r, prev_color: le, next_color: ri, inward: b }) } else { None },
                Side::Right  => if ri == BORDER { Some(EdgePlacement { pid: p.id, rot: r, prev_color: t,  next_color: b,  inward: le }) } else { None },
                Side::Bottom => if b == BORDER  { Some(EdgePlacement { pid: p.id, rot: r, prev_color: ri, next_color: le, inward: t }) } else { None },
                Side::Left   => if le == BORDER { Some(EdgePlacement { pid: p.id, rot: r, prev_color: b,  next_color: t,  inward: ri }) } else { None },
            };
            if let Some(pp) = placement { out.push(pp); }
        }
    }
    out
}

#[derive(Clone)]
struct PathFinder<'a> {
    by_prev: BTreeMap<u8, Vec<&'a EdgePlacement>>,
    length: usize,
    end_color: u8,
}

impl<'a> PathFinder<'a> {
    fn new(eps: &'a [EdgePlacement], length: usize, end_color: u8) -> Self {
        let mut by_prev: BTreeMap<u8, Vec<&'a EdgePlacement>> = BTreeMap::new();
        for ep in eps {
            by_prev.entry(ep.prev_color).or_default().push(ep);
        }
        Self { by_prev, length, end_color }
    }

    /// Try to find ONE valid path starting from `start_color` with the
    /// given used-pieces mask (256-bit). Random rotation of candidate
    /// order at each node. Returns Some(Vec<EdgePlacement>) on success.
    /// Mutates the rng state.
    fn sample_path(
        &self,
        start_color: u8,
        used_mask: &[u64; 4],
        rng: &mut SimpleRng,
        node_budget: u64,
    ) -> Option<Vec<EdgePlacement>> {
        let mut local_used = *used_mask;
        let mut current: Vec<EdgePlacement> = Vec::with_capacity(self.length);
        let mut nodes = 0u64;
        if self.recurse(0, start_color, &mut local_used, &mut current, rng, &mut nodes, node_budget) {
            Some(current)
        } else {
            None
        }
    }

    fn recurse(
        &self,
        idx: usize,
        required_prev: u8,
        used: &mut [u64; 4],
        current: &mut Vec<EdgePlacement>,
        rng: &mut SimpleRng,
        nodes: &mut u64,
        node_budget: u64,
    ) -> bool {
        *nodes += 1;
        if *nodes > node_budget { return false; }
        if idx == self.length {
            return current.last().map(|p| p.next_color) == Some(self.end_color);
        }
        let opts = match self.by_prev.get(&required_prev) {
            Some(v) => v.clone(),
            None => return false,
        };
        // Shuffle opts
        let mut shuffled = opts;
        let n = shuffled.len();
        for i in (1..n).rev() {
            let j = rng.next_u64() as usize % (i + 1);
            shuffled.swap(i, j);
        }
        let last = idx == self.length - 1;
        for ep in shuffled {
            if has_bit(used, ep.pid) { continue; }
            if last && ep.next_color != self.end_color { continue; }
            set_bit(used, ep.pid);
            current.push(*ep);
            if self.recurse(idx + 1, ep.next_color, used, current, rng, nodes, node_budget) {
                return true;
            }
            current.pop();
            clear_bit(used, ep.pid);
            if *nodes > node_budget { return false; }
        }
        false
    }
}

#[inline]
fn set_bit(mask: &mut [u64; 4], pid: PieceId) {
    let p = pid as usize;
    mask[p / 64] |= 1u64 << (p % 64);
}
#[inline]
fn clear_bit(mask: &mut [u64; 4], pid: PieceId) {
    let p = pid as usize;
    mask[p / 64] &= !(1u64 << (p % 64));
}
#[inline]
fn has_bit(mask: &[u64; 4], pid: PieceId) -> bool {
    let p = pid as usize;
    (mask[p / 64] >> (p % 64)) & 1 == 1
}

// Simple xorshift64* RNG (good enough for shuffling)
struct SimpleRng { state: u64 }
impl SimpleRng {
    fn new(seed: u64) -> Self { Self { state: if seed == 0 { 0xDEADBEEFCAFEBABE } else { seed } } }
    fn next_u64(&mut self) -> u64 {
        let mut x = self.state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.state = x;
        x.wrapping_mul(0x2545F4914F6CDD1D)
    }
    #[allow(dead_code)]
    fn shuffle<T>(&mut self, v: &mut [T]) {
        for i in (1..v.len()).rev() {
            let j = self.next_u64() as usize % (i + 1);
            v.swap(i, j);
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).map_err(|e| format!("{e}"))?;
    let size = puzzle.width;
    eprintln!("puzzle: {}x{}, {} pieces", size, size, puzzle.pieces().len());

    let tl = corner_placements(puzzle.pieces(), CornerKind::TL);
    let tr = corner_placements(puzzle.pieces(), CornerKind::TR);
    let br = corner_placements(puzzle.pieces(), CornerKind::BR);
    let bl = corner_placements(puzzle.pieces(), CornerKind::BL);
    eprintln!("corners: TL={} TR={} BR={} BL={}", tl.len(), tr.len(), br.len(), bl.len());

    let top_eps = edge_placements(puzzle.pieces(), Side::Top);
    let right_eps = edge_placements(puzzle.pieces(), Side::Right);
    let bottom_eps = edge_placements(puzzle.pieces(), Side::Bottom);
    let left_eps = edge_placements(puzzle.pieces(), Side::Left);
    eprintln!("edges/side: top={} right={} bottom={} left={}",
              top_eps.len(), right_eps.len(), bottom_eps.len(), left_eps.len());

    let side_len = (size as usize) - 2;
    let mut rng = SimpleRng::new(args.seed);

    // Build the list of distinct corner-quads (unique pids; rotation forced).
    // 4 TL × 4 TR × 4 BR × 4 BL = 256 raw, but each corner has 4 distinct corner-pieces in E2, so we need pid distinctness across the quad. = 4! = 24 valid quads (one per permutation).
    let mut corner_quads: Vec<(CornerPlacement, CornerPlacement, CornerPlacement, CornerPlacement)> = Vec::new();
    for &tlp in &tl {
        for &trp in &tr {
            if trp.pid == tlp.pid { continue; }
            for &brp in &br {
                if brp.pid == tlp.pid || brp.pid == trp.pid { continue; }
                for &blp in &bl {
                    if blp.pid == tlp.pid || blp.pid == trp.pid || blp.pid == brp.pid { continue; }
                    corner_quads.push((tlp, trp, brp, blp));
                }
            }
        }
    }
    eprintln!("distinct corner-quads: {}", corner_quads.len());

    // Output writer
    if let Some(parent) = args.out.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let mut writer = BufWriter::new(File::create(&args.out)?);

    let deadline = Instant::now() + std::time::Duration::from_secs(args.time_budget);
    let t0 = Instant::now();
    let mut found_count = 0usize;
    let mut samples = 0u64;
    let mut last_log_samples = 0u64;
    use std::collections::HashSet;
    let mut signatures: HashSet<u64> = HashSet::new();

    while Instant::now() < deadline && found_count < args.n_target {
        samples += 1;
        if samples - last_log_samples >= args.log_every {
            eprintln!(
                "  samples={} found={} elapsed={:.1}s ({:.0} samples/s)",
                samples, found_count, t0.elapsed().as_secs_f64(),
                samples as f64 / t0.elapsed().as_secs_f64().max(1e-9)
            );
            last_log_samples = samples;
        }

        let q = &corner_quads[(rng.next_u64() as usize) % corner_quads.len()];
        let (tlp, trp, brp, blp) = (q.0, q.1, q.2, q.3);

        // Mark corner pids as used (corner pieces 0..3 typically; out-of-bag for edges).
        let mut used = [0u64; 4];
        set_bit(&mut used, tlp.pid);
        set_bit(&mut used, trp.pid);
        set_bit(&mut used, brp.pid);
        set_bit(&mut used, blp.pid);

        // Sample top side
        let top_finder = PathFinder::new(&top_eps, side_len, trp.incoming);
        let top_path = match top_finder.sample_path(tlp.outgoing, &used, &mut rng, args.side_node_budget) {
            Some(p) => p,
            None => continue,
        };
        for ep in &top_path { set_bit(&mut used, ep.pid); }

        // Sample right side
        let right_finder = PathFinder::new(&right_eps, side_len, brp.incoming);
        let right_path = match right_finder.sample_path(trp.outgoing, &used, &mut rng, args.side_node_budget) {
            Some(p) => p,
            None => continue,
        };
        for ep in &right_path { set_bit(&mut used, ep.pid); }

        // Sample bottom side
        let bottom_finder = PathFinder::new(&bottom_eps, side_len, blp.incoming);
        let bottom_path = match bottom_finder.sample_path(brp.outgoing, &used, &mut rng, args.side_node_budget) {
            Some(p) => p,
            None => continue,
        };
        for ep in &bottom_path { set_bit(&mut used, ep.pid); }

        // Sample left side
        let left_finder = PathFinder::new(&left_eps, side_len, tlp.incoming);
        let left_path = match left_finder.sample_path(blp.outgoing, &used, &mut rng, args.side_node_budget) {
            Some(p) => p,
            None => continue,
        };

        // Build a stable signature over the 60 (pid, rot) cells in walk order
        // for de-duplication.
        let mut sig_data: Vec<(PieceId, u8)> = Vec::with_capacity(60);
        sig_data.push((tlp.pid, tlp.rot));
        for ep in &top_path { sig_data.push((ep.pid, ep.rot)); }
        sig_data.push((trp.pid, trp.rot));
        for ep in &right_path { sig_data.push((ep.pid, ep.rot)); }
        sig_data.push((brp.pid, brp.rot));
        for ep in &bottom_path { sig_data.push((ep.pid, ep.rot)); }
        sig_data.push((blp.pid, blp.rot));
        for ep in &left_path { sig_data.push((ep.pid, ep.rot)); }

        let mut hasher: u64 = 0xcbf29ce484222325;
        for (pid, rot) in &sig_data {
            hasher ^= *pid as u64;
            hasher = hasher.wrapping_mul(0x100000001b3);
            hasher ^= *rot as u64;
            hasher = hasher.wrapping_mul(0x100000001b3);
        }
        if !signatures.insert(hasher) { continue; }

        // Emit JSON
        let arr: Vec<serde_json::Value> = sig_data.iter().map(|(p, r)| serde_json::json!([p, r])).collect();
        writeln!(writer, "{}", serde_json::to_string(&serde_json::json!({"border": arr}))?)?;
        found_count += 1;
    }
    writer.flush()?;

    eprintln!(
        "\n=== TOTAL: {} distinct borders in {:.1}s ({} samples; success rate {:.2}%) ===",
        found_count,
        t0.elapsed().as_secs_f64(),
        samples,
        100.0 * found_count as f64 / samples.max(1) as f64
    );
    Ok(())
}
