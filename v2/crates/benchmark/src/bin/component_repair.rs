// Component-targeted mini-CP repair (Option A followup, F2 formulation).
//
// Vol. 4 finding: at the canonical 449 plateau, the 31 mismatch edges
// cluster into one large (38-cell) component and 3 small ones. Vol. 2
// already showed rectangle-window repair (free a k×k box, pin the rest)
// fails — the obstruction is in the pinned cells.
//
// This bin tests a different formulation: free *only* the
// mismatch-incident cells of a chosen component, keep all 256 - |comp|
// other cells pinned (including the matched-edge neighbors of the
// component). The piece pool that CP has to work with is exactly the
// pieces currently placed in component cells. If CP finds *any*
// permutation that scores higher than the plateau, we have a real edge
// gain. If CP proves infeasibility or only re-finds the same
// permutation, we've confirmed that *closed in-pool permutation* of
// the component cannot improve the score — pushing the diagnostic
// toward Option C (SAT) for an exact bound.
//
// Inputs:
//   - enriched pt_e2 / edge_cp_e2 JSON (must have `placement`) OR
//     legacy format (bucas decode fallback)
//   - plateau_analysis_*.json (the components_json output)
//   - component index (0 = largest, ...)

use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Hint, Hints, Piece, PieceId, Puzzle, Rotation, BORDER};
use eternity2_events::BufferSink;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};
use serde_json::Value;

#[derive(Parser, Debug)]
#[command(name = "component_repair", about = "Free a mismatch component and re-CP it with a closed pool")]
struct Args {
    /// Plateau JSON (with `placement` or `bucas_url`).
    #[arg(long)]
    plateau: PathBuf,

    /// plateau_analysis JSON (produced by plateau_analyze).
    #[arg(long)]
    analysis: PathBuf,

    /// Component index (0 = largest, sorted by size desc).
    #[arg(long, default_value_t = 0)]
    component: usize,

    /// CP time budget (seconds).
    #[arg(long, default_value_t = 60)]
    budget_seconds: u64,

    /// Puzzle CSV.
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Also try freeing a *padded* version (component cells + their 4-neighbors).
    /// Useful if the closed-pool version fails — gives CP more room.
    #[arg(long, default_value_t = false)]
    padded: bool,

    /// Free ALL mismatch components simultaneously (default true). The
    /// solver-engine refuses hint sets where the pinned cells contain
    /// any color mismatch, so pinning cells from non-target components
    /// fails. Pass --target-only to test only the target component.
    #[arg(long, default_value_t = false)]
    target_only: bool,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.piece(id)
}

fn decode_from_bucas(puzzle: &Puzzle, bucas_url: &str) -> Vec<Option<(PieceId, Rotation)>> {
    let n_cells = puzzle.cell_count() as usize;
    let mut out = vec![None; n_cells];
    let Some(idx) = bucas_url.find("board_edges=") else { return out };
    let blob = &bucas_url[idx + "board_edges=".len()..];
    let blob = blob.split('&').next().unwrap_or(blob);
    let bytes = blob.as_bytes();
    if bytes.len() < n_cells * 4 { return out; }
    for pos in 0..n_cells {
        let q: [u8; 4] = std::array::from_fn(|i| bytes[pos * 4 + i] - b'a');
        if q.iter().all(|&c| c == 0) { continue; }
        let mut found: Option<(PieceId, Rotation)> = None;
        let mut multi = false;
        'pieces: for piece in puzzle.pieces() {
            for rot in Rotation::ALL {
                let e = piece.edges.rotated(rot).as_array();
                if e == q {
                    if found.is_some() { multi = true; break 'pieces; }
                    found = Some((piece.id, rot));
                }
            }
        }
        if !multi { out[pos] = found; }
    }
    out
}

fn parse_placement_field(v: &Value, puzzle: &Puzzle) -> Option<Vec<Option<(PieceId, Rotation)>>> {
    let arr = v.as_array()?;
    if arr.len() != puzzle.cell_count() as usize { return None; }
    let mut out = Vec::with_capacity(arr.len());
    for entry in arr {
        if entry.is_null() { out.push(None); }
        else {
            let pid = entry.get("piece_id")?.as_u64()? as PieceId;
            let rot_u = entry.get("rotation")?.as_u64()? as u8;
            out.push(Some((pid, Rotation::from_u8(rot_u)?)));
        }
    }
    Some(out)
}

fn load_placement(plateau_json: &Value, puzzle: &Puzzle) -> Vec<Option<(PieceId, Rotation)>> {
    if let Some(p) = plateau_json.get("placement") {
        if let Some(parsed) = parse_placement_field(p, puzzle) {
            eprintln!("using enriched `placement` field");
            return parsed;
        }
    }
    let url = plateau_json.get("bucas_url").and_then(|x| x.as_str()).expect("bucas_url");
    eprintln!("decoding placement from bucas_url");
    decode_from_bucas(puzzle, url)
}

fn build_board(puzzle: &Puzzle, placement: &[Option<(PieceId, Rotation)>]) -> Board {
    let mut b = Board::empty(puzzle);
    for (pos, slot) in placement.iter().enumerate() {
        if let Some((pid, rot)) = slot {
            b.place(pos as u32, *pid, *rot);
        }
    }
    b
}

fn score_board(puzzle: &Puzzle, board: &Board) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut m = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(p) = lookup_piece(puzzle, pid) else { continue };
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 { m += 1; }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER && e[2] != 0 { m += 1; }
                    }
                }
            }
        }
    }
    m
}

fn load_component_cells(analysis: &Value, idx: usize) -> Vec<u32> {
    let comps = analysis.get("components").and_then(|x| x.as_array()).expect("components");
    if idx >= comps.len() { panic!("component index {} out of range (n={})", idx, comps.len()); }
    let arr = comps[idx].get("cells").and_then(|x| x.as_array()).expect("cells");
    arr.iter().map(|v| v.as_u64().unwrap() as u32).collect()
}

fn load_all_mismatch_cells(analysis: &Value) -> Vec<u32> {
    let comps = analysis.get("components").and_then(|x| x.as_array()).expect("components");
    let mut out: BTreeSet<u32> = BTreeSet::new();
    for c in comps {
        if let Some(arr) = c.get("cells").and_then(|x| x.as_array()) {
            for v in arr { if let Some(n) = v.as_u64() { out.insert(n as u32); } }
        }
    }
    out.into_iter().collect()
}

fn padded_set(cells: &[u32], w: u32, h: u32) -> BTreeSet<u32> {
    let mut set: BTreeSet<u32> = cells.iter().copied().collect();
    for &pos in cells {
        let x = pos % w;
        let y = pos / w;
        for (dx, dy) in [(1i32, 0i32), (-1, 0), (0, 1), (0, -1)] {
            let nx = x as i32 + dx;
            let ny = y as i32 + dy;
            if nx < 0 || ny < 0 || nx as u32 >= w || ny as u32 >= h { continue; }
            set.insert(ny as u32 * w + nx as u32);
        }
    }
    set
}

fn run_repair(
    puzzle: &Puzzle,
    placement: &[Option<(PieceId, Rotation)>],
    free_cells: &BTreeSet<u32>,
    budget_ms: u64,
    label: &str,
) -> (Option<Board>, u32, SolveOutcome) {
    eprintln!("\n--- {} ---", label);
    eprintln!("freeing {} cells, pinning {} cells", free_cells.len(), 256 - free_cells.len());

    let mut hs: Vec<Hint> = Vec::new();
    for (pos, slot) in placement.iter().enumerate() {
        if free_cells.contains(&(pos as u32)) { continue; }
        if let Some((pid, rot)) = slot {
            hs.push(Hint { position: pos as u32, piece_id: *pid, rotation: *rot });
        }
    }
    let hints = Hints::new(hs);

    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.hints = hints;

    let t0 = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let dt = t0.elapsed();
    eprintln!("CP elapsed: {:.2}s", dt.as_secs_f64());

    let board_opt = match &outcome {
        SolveOutcome::Solved(b) => Some(b.clone()),
        SolveOutcome::TimedOut { best_partial, .. }
        | SolveOutcome::Cancelled { best_partial, .. } => Some(best_partial.clone()),
        SolveOutcome::AllSolutions(bs) => bs.first().cloned(),
        _ => None,
    };

    let score = board_opt.as_ref().map(|b| score_board(puzzle, b)).unwrap_or(0);
    let outcome_dbg = match &outcome {
        SolveOutcome::Solved(_) => "Solved".to_string(),
        SolveOutcome::TimedOut { .. } => "TimedOut".to_string(),
        SolveOutcome::Cancelled { .. } => "Cancelled".to_string(),
        SolveOutcome::Exhausted => "Exhausted (infeasible)".to_string(),
        SolveOutcome::AllSolutions(bs) => format!("AllSolutions({})", bs.len()),
        SolveOutcome::Error(e) => format!("Error({})", e),
    };
    eprintln!("outcome: {}, new score: {}", outcome_dbg, score);

    (board_opt, score, outcome)
}

fn main() {
    let args = Args::parse();
    let (puzzle, _) = load_puzzle_with_hints(&args.puzzle).expect("load puzzle");
    eprintln!("loaded {}x{}, {} pieces, {} colors",
        puzzle.width, puzzle.height, puzzle.pieces().len(), puzzle.color_count - 1);

    let plateau_v: Value = serde_json::from_str(&fs::read_to_string(&args.plateau).expect("read plateau"))
        .expect("parse plateau");
    let analysis_v: Value = serde_json::from_str(&fs::read_to_string(&args.analysis).expect("read analysis"))
        .expect("parse analysis");

    let placement = load_placement(&plateau_v, &puzzle);
    let base_board = build_board(&puzzle, &placement);
    let base_score = score_board(&puzzle, &base_board);
    eprintln!("baseline plateau score: {}/480", base_score);

    let target_cells = load_component_cells(&analysis_v, args.component);
    eprintln!("target component {}: {} cells", args.component, target_cells.len());
    let cells: Vec<u32> = if args.target_only {
        eprintln!("target_only=true: freeing only the target component");
        target_cells.clone()
    } else {
        let all = load_all_mismatch_cells(&analysis_v);
        eprintln!("freeing all {} mismatch-incident cells (default)", all.len());
        all
    };

    let w = puzzle.width;
    let h = puzzle.height;
    let budget_ms = args.budget_seconds * 1000;

    // F2-tight: free only component cells.
    let free_tight: BTreeSet<u32> = cells.iter().copied().collect();
    let (b_tight, s_tight, _o_tight) =
        run_repair(&puzzle, &placement, &free_tight, budget_ms, "F2-tight (component cells only)");
    let delta_tight = s_tight as i32 - base_score as i32;
    eprintln!("Δ score (tight): {:+}", delta_tight);

    // Optionally also a padded version.
    if args.padded {
        let free_padded = padded_set(&cells, w, h);
        let (b_padded, s_padded, _o_padded) =
            run_repair(&puzzle, &placement, &free_padded, budget_ms, "F2-padded (component + 4-neighbors)");
        let delta_padded = s_padded as i32 - base_score as i32;
        eprintln!("Δ score (padded): {:+}", delta_padded);
        let _ = b_padded;
    }
    let _ = b_tight;

    eprintln!("\nDone.");
}
