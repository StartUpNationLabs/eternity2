// Plateau structural diagnostic — Option A from RESEARCH_NOTES_3 SESSION CLOSE.
//
// Given a plateau snapshot (cell-CP→PT or edge-CP→PT JSON written by
// report.rs), compute:
//   - mismatch edges (the (480 − score) interior edges where the two
//     incident cells disagree on color)
//   - mismatch-cell connected components (cells touching ≥1 mismatch,
//     linked if they're 4-grid-adjacent)
//   - per-component bounding boxes, sizes, and ASCII overlay
//   - Hall-deficiency proxy on (mismatch-cells × pieces filterable by
//     the fixed surrounding boundary)
//
// The output answers the structural question that shapes B-vs-C:
// localized clusters → build mini-CP region repair; distributed →
// confirms 449 as a hard ceiling and pushes toward SAT (Option C).
//
// Input formats accepted:
//   1. enriched report.rs output (preferred): top-level `placement`
//      field — array of {piece_id,rotation}|null per cell.
//   2. legacy report.rs output: only `bucas_url` — decoded by
//      matching each cell's 4-tuple against the piece-rotation catalog.

use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Piece, PieceId, Puzzle, Rotation, BORDER};
use serde_json::{json, Value};

#[derive(Parser, Debug)]
#[command(name = "plateau_analyze", about = "Structural diagnostic of an E2 plateau state")]
struct Args {
    /// Plateau JSON (pt_e2 or edge_cp_e2 report).
    #[arg(long)]
    input: PathBuf,

    /// Puzzle CSV.
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Output JSON path. Defaults to output/plateau_analysis_<stem>.json.
    #[arg(long)]
    output: Option<PathBuf>,

    /// Print full ASCII board overlay (slow on terminals without color).
    #[arg(long, default_value_t = true)]
    overlay: bool,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.piece(id)
}

// Re-derive cell→(piece, rotation) from the bucas board_edges blob.
// Each cell carries 4 colors (top, right, bottom, left); match against the
// piece-rotation catalog. Returns None for cells with no match or with
// ambiguous matches (collision noted in stats).
fn decode_from_bucas(puzzle: &Puzzle, bucas_url: &str) -> Vec<Option<(PieceId, Rotation)>> {
    let n_cells = puzzle.cell_count() as usize;
    let mut out = vec![None; n_cells];
    let Some(idx) = bucas_url.find("board_edges=") else { return out };
    let blob = &bucas_url[idx + "board_edges=".len()..];
    let blob = blob.split('&').next().unwrap_or(blob);
    let bytes = blob.as_bytes();
    if bytes.len() < n_cells * 4 {
        return out;
    }
    for pos in 0..n_cells {
        let q: [u8; 4] = std::array::from_fn(|i| bytes[pos * 4 + i] - b'a');
        if q.iter().all(|&c| c == 0) {
            continue; // empty cell or all-border (degenerate)
        }
        // Find unique piece-rotation matching this 4-tuple.
        let mut found: Option<(PieceId, Rotation)> = None;
        let mut multi = false;
        'pieces: for piece in puzzle.pieces() {
            for rot in Rotation::ALL {
                let e = piece.edges.rotated(rot).as_array();
                if e == q {
                    if found.is_some() {
                        multi = true;
                        break 'pieces;
                    }
                    found = Some((piece.id, rot));
                }
            }
        }
        if !multi {
            out[pos] = found;
        }
    }
    out
}

fn parse_placement_field(v: &Value, puzzle: &Puzzle) -> Option<Vec<Option<(PieceId, Rotation)>>> {
    let arr = v.as_array()?;
    if arr.len() != puzzle.cell_count() as usize {
        return None;
    }
    let mut out = Vec::with_capacity(arr.len());
    for entry in arr {
        if entry.is_null() {
            out.push(None);
        } else {
            let pid = entry.get("piece_id")?.as_u64()? as PieceId;
            let rot_u = entry.get("rotation")?.as_u64()? as u8;
            let rot = Rotation::from_u8(rot_u)?;
            out.push(Some((pid, rot)));
        }
    }
    Some(out)
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

#[derive(Debug, Clone)]
struct MismatchEdge {
    // Cells (row-major positions); always a < b. Orientation captures it:
    // Horizontal: a = (r, c), b = (r, c+1)
    // Vertical:   a = (r, c), b = (r+1, c)
    a: u32,
    b: u32,
    horizontal: bool,
    color_a: u8, // color on cell-a's side
    color_b: u8, // color on cell-b's side
}

fn compute_mismatches(puzzle: &Puzzle, board: &Board) -> (Vec<MismatchEdge>, u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let total = (w - 1) * h + w * (h - 1);
    let mut matches = 0u32;
    let mut mismatches: Vec<MismatchEdge> = Vec::new();
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(p) = lookup_piece(puzzle, pid) else { continue };
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                let rpos = y * w + (x + 1);
                if let Some((rpid, rrot)) = board.get(rpos) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        let (ca, cb) = (e[1], re[3]);
                        if ca != BORDER && cb != BORDER && ca != 0 && cb != 0 {
                            if ca == cb {
                                matches += 1;
                            } else {
                                mismatches.push(MismatchEdge {
                                    a: pos, b: rpos, horizontal: true,
                                    color_a: ca, color_b: cb,
                                });
                            }
                        }
                    }
                }
            }
            if y + 1 < h {
                let bpos = (y + 1) * w + x;
                if let Some((bpid, brot)) = board.get(bpos) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        let (ca, cb) = (e[2], be[0]);
                        if ca != BORDER && cb != BORDER && ca != 0 && cb != 0 {
                            if ca == cb {
                                matches += 1;
                            } else {
                                mismatches.push(MismatchEdge {
                                    a: pos, b: bpos, horizontal: false,
                                    color_a: ca, color_b: cb,
                                });
                            }
                        }
                    }
                }
            }
        }
    }
    (mismatches, matches, total)
}

// Union-find over cells; mismatch-incident cells are linked if they are
// 4-grid-adjacent.
struct DSU {
    parent: Vec<u32>,
}
impl DSU {
    fn new(n: usize) -> Self { Self { parent: (0..n as u32).collect() } }
    fn find(&mut self, x: u32) -> u32 {
        let mut r = x;
        while self.parent[r as usize] != r { r = self.parent[r as usize]; }
        let mut cur = x;
        while self.parent[cur as usize] != r {
            let nx = self.parent[cur as usize];
            self.parent[cur as usize] = r;
            cur = nx;
        }
        r
    }
    fn union(&mut self, a: u32, b: u32) {
        let ra = self.find(a);
        let rb = self.find(b);
        if ra != rb { self.parent[ra as usize] = rb; }
    }
}

#[derive(Debug)]
struct Component {
    cells: Vec<u32>, // row-major positions, sorted
    bbox: (u32, u32, u32, u32), // (min_x, min_y, max_x, max_y)
    mismatch_edges_inside: u32,
    mismatch_edges_on_boundary: u32, // edges where one endpoint is in, one out
}

fn compute_components(puzzle: &Puzzle, mismatches: &[MismatchEdge]) -> Vec<Component> {
    let w = puzzle.width;
    let n_cells = puzzle.cell_count() as usize;
    let mut incident: BTreeSet<u32> = BTreeSet::new();
    for m in mismatches {
        incident.insert(m.a);
        incident.insert(m.b);
    }
    let mut dsu = DSU::new(n_cells);
    // Link 4-adjacent incident cells.
    let incident_arr: Vec<u32> = incident.iter().copied().collect();
    for &pos in &incident_arr {
        let x = pos % w;
        let y = pos / w;
        for (dx, dy) in [(1i32, 0i32), (-1, 0), (0, 1), (0, -1)] {
            let nx = x as i32 + dx;
            let ny = y as i32 + dy;
            if nx < 0 || ny < 0 || nx as u32 >= w || ny as u32 >= puzzle.height { continue; }
            let npos = ny as u32 * w + nx as u32;
            if incident.contains(&npos) {
                dsu.union(pos, npos);
            }
        }
    }
    // Bucket by root.
    use std::collections::BTreeMap;
    let mut buckets: BTreeMap<u32, Vec<u32>> = BTreeMap::new();
    for &pos in &incident_arr {
        let r = dsu.find(pos);
        buckets.entry(r).or_default().push(pos);
    }
    let mut components: Vec<Component> = Vec::with_capacity(buckets.len());
    for (_root, mut cells) in buckets {
        cells.sort_unstable();
        let mut minx = u32::MAX;
        let mut miny = u32::MAX;
        let mut maxx = 0u32;
        let mut maxy = 0u32;
        let cell_set: BTreeSet<u32> = cells.iter().copied().collect();
        for &pos in &cells {
            let x = pos % w;
            let y = pos / w;
            minx = minx.min(x); miny = miny.min(y);
            maxx = maxx.max(x); maxy = maxy.max(y);
        }
        let mut inside = 0u32;
        let mut on_bdry = 0u32;
        for m in mismatches {
            let ain = cell_set.contains(&m.a);
            let bin = cell_set.contains(&m.b);
            match (ain, bin) {
                (true, true) => inside += 1,
                (true, false) | (false, true) => on_bdry += 1,
                _ => {}
            }
        }
        components.push(Component {
            cells,
            bbox: (minx, miny, maxx, maxy),
            mismatch_edges_inside: inside,
            mismatch_edges_on_boundary: on_bdry,
        });
    }
    components.sort_by(|a, b| b.cells.len().cmp(&a.cells.len()));
    components
}

fn ascii_overlay(puzzle: &Puzzle, mismatches: &[MismatchEdge], components: &[Component]) -> String {
    let w = puzzle.width as usize;
    let h = puzzle.height as usize;
    // Map cell → component index (1-based for human display).
    let mut comp_of: Vec<i32> = vec![-1; w * h];
    for (i, c) in components.iter().enumerate() {
        for &pos in &c.cells {
            comp_of[pos as usize] = i as i32;
        }
    }
    let mut h_mis: Vec<bool> = vec![false; w * h];
    let mut v_mis: Vec<bool> = vec![false; w * h];
    for m in mismatches {
        if m.horizontal { h_mis[m.a as usize] = true; }
        else            { v_mis[m.a as usize] = true; }
    }
    // 3 chars per cell horizontally: " X " or label + h-edge marker between cells.
    // Two text rows per cell row: cell-row, then v-edge-marker row.
    let mut out = String::new();
    let label = |i: i32| -> char {
        if i < 0 { ' ' }
        else if i < 9 { (b'1' + i as u8) as char }
        else if i < 35 { (b'a' + (i - 9) as u8) as char }
        else { '*' }
    };
    out.push_str("   ");
    for x in 0..w { out.push_str(&format!(" {:2}", x)); }
    out.push('\n');
    for y in 0..h {
        out.push_str(&format!("{:2} ", y));
        for x in 0..w {
            let pos = y * w + x;
            let c = comp_of[pos];
            let ch = if c >= 0 { label(c) } else { '.' };
            out.push(' ');
            out.push(ch);
            if x + 1 < w {
                out.push(if h_mis[pos] { '|' } else { ' ' });
            }
        }
        out.push('\n');
        if y + 1 < h {
            out.push_str("   ");
            for x in 0..w {
                let pos = y * w + x;
                out.push(' ');
                out.push(if v_mis[pos] { '-' } else { ' ' });
                if x + 1 < w { out.push(' '); }
            }
            out.push('\n');
        }
    }
    out
}

fn main() {
    let args = Args::parse();
    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).expect("load puzzle");
    eprintln!("loaded puzzle {}x{}, {} pieces, {} colors",
        puzzle.width, puzzle.height, puzzle.pieces().len(), puzzle.color_count - 1);

    let raw = fs::read_to_string(&args.input).expect("read input");
    let v: Value = serde_json::from_str(&raw).expect("parse input");

    let placement: Vec<Option<(PieceId, Rotation)>> = if let Some(p) = v.get("placement") {
        match parse_placement_field(p, &puzzle) {
            Some(parsed) => { eprintln!("using enriched `placement` field"); parsed }
            None => {
                eprintln!("WARN: `placement` present but malformed; falling back to bucas decode");
                let url = v.get("bucas_url").and_then(|x| x.as_str()).expect("bucas_url");
                decode_from_bucas(&puzzle, url)
            }
        }
    } else if let Some(url) = v.get("bucas_url").and_then(|x| x.as_str()) {
        eprintln!("no `placement` field; decoding from bucas_url");
        decode_from_bucas(&puzzle, url)
    } else {
        panic!("input has neither `placement` nor `bucas_url`");
    };

    let placed: u32 = placement.iter().filter(|c| c.is_some()).count() as u32;
    let n_cells = puzzle.cell_count();
    eprintln!("placement decoded: {}/{} cells", placed, n_cells);

    // Duplicate-piece check (sanity for bucas decode path).
    {
        use std::collections::HashMap;
        let mut counts: HashMap<PieceId, u32> = HashMap::new();
        for slot in &placement {
            if let Some((pid, _)) = slot { *counts.entry(*pid).or_insert(0) += 1; }
        }
        let dups: Vec<(PieceId, u32)> = counts.iter().filter(|(_, n)| **n > 1).map(|(p, n)| (*p, *n)).collect();
        if !dups.is_empty() {
            eprintln!("WARN: {} pieces appear multiple times in placement", dups.len());
        }
    }

    let board = build_board(&puzzle, &placement);
    let (mismatches, matched, total) = compute_mismatches(&puzzle, &board);
    eprintln!("score: {}/{} matched, {} mismatched", matched, total, mismatches.len());

    let components = compute_components(&puzzle, &mismatches);
    eprintln!("mismatch-incident components: {}", components.len());
    let sizes: Vec<usize> = components.iter().map(|c| c.cells.len()).collect();
    eprintln!("component sizes: {:?}", sizes);
    let largest = sizes.iter().copied().max().unwrap_or(0);
    eprintln!("largest component: {} cells", largest);

    if args.overlay {
        let s = ascii_overlay(&puzzle, &mismatches, &components);
        eprintln!("\nBoard overlay (digit/letter = component, | = h-mismatch, - = v-mismatch):\n{}", s);
    }

    // ----- Diagnostic interpretation -----
    // Spatial localization: max(component_size) / n_mismatch_cells.
    // If ~1.0: one big blob → highly localized but possibly too large for
    // mini-CP. If << 1.0 with many small components: distributed-but-local.
    // If many singletons: distributed → structural ceiling more likely.
    let total_incident: usize = sizes.iter().sum();
    let localization = if total_incident == 0 { 0.0 }
                       else { largest as f64 / total_incident as f64 };
    eprintln!("\nLocalization ratio (largest / total_incident): {:.3}", localization);
    eprintln!("Interpretation guide:");
    eprintln!("  >= 0.50  → mostly-single-blob: one localized cluster, target with mini-CP");
    eprintln!("  0.20–0.50 → few moderate clusters: per-cluster mini-CP plausible");
    eprintln!("  < 0.20   → distributed: ceiling likely structural, recommend Option C (SAT)");

    let components_json: Vec<Value> = components.iter().map(|c| json!({
        "size": c.cells.len(),
        "bbox": [c.bbox.0, c.bbox.1, c.bbox.2, c.bbox.3],
        "cells": c.cells,
        "mismatch_edges_inside": c.mismatch_edges_inside,
        "mismatch_edges_on_boundary": c.mismatch_edges_on_boundary,
    })).collect();

    let mismatches_json: Vec<Value> = mismatches.iter().map(|m| json!({
        "a": m.a, "b": m.b, "horizontal": m.horizontal,
        "color_a": m.color_a, "color_b": m.color_b,
    })).collect();

    let analysis = json!({
        "source": args.input.display().to_string(),
        "score": {"matched_edges": matched, "total_edges": total, "n_mismatches": mismatches.len()},
        "placement_decoded_cells": placed,
        "n_components": components.len(),
        "component_sizes": sizes,
        "largest_component_cells": largest,
        "localization_ratio": localization,
        "components": components_json,
        "mismatches": mismatches_json,
    });

    let stem = args.input.file_stem().and_then(|s| s.to_str()).unwrap_or("plateau");
    let out_path = args.output.unwrap_or_else(|| {
        PathBuf::from("output").join(format!("plateau_analysis_{}.json", stem))
    });
    fs::create_dir_all(out_path.parent().unwrap_or_else(|| std::path::Path::new("."))).ok();
    fs::write(&out_path, serde_json::to_string_pretty(&analysis).unwrap()).expect("write");
    eprintln!("\nWrote {}", out_path.display());
}
