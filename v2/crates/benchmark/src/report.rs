// End-of-run reporting: writes a JSON stats file plus a clickable Bucas URL
// for the final board into an output directory. Used by all benchmark
// binaries so every run leaves a postmortem on disk.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};
use serde_json::{json, Value};

// Bucas viewer at e2.bucas.name encodes each tile as 4 letters (top, right,
// bottom, left). Color 0 (BORDER) maps to 'a'; inner colors 1..=22 map to
// 'b'..='w'. Empty cells encode as "aaaa" — same as a fully grey border tile.
fn color_to_bucas(c: u8) -> char {
    if c as usize > 22 {
        // Defensive: out-of-range — fall back to 'a' rather than panic on output.
        return 'a';
    }
    (b'a' + c) as char
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.piece(id)
}

pub fn board_to_bucas_edges(puzzle: &Puzzle, board: &Board) -> String {
    let mut s = String::with_capacity((puzzle.cell_count() as usize) * 4);
    for pos in 0..puzzle.cell_count() {
        match board.get(pos) {
            Some((pid, rot)) => {
                if let Some(piece) = lookup_piece(puzzle, pid) {
                    let e = piece.edges.rotated(rot).as_array();
                    s.push(color_to_bucas(e[0]));
                    s.push(color_to_bucas(e[1]));
                    s.push(color_to_bucas(e[2]));
                    s.push(color_to_bucas(e[3]));
                } else {
                    s.push_str("aaaa");
                }
            }
            None => s.push_str("aaaa"),
        }
    }
    s
}

pub fn bucas_url(puzzle: &Puzzle, board: &Board, puzzle_name: &str) -> String {
    let edges = board_to_bucas_edges(puzzle, board);
    // Bucas's default motifs_order matches our color labeling (pieces.txt
    // canonical order); explicitly setting motifs_order=jblackwood scrambles
    // the rendering, so we omit it.
    format!(
        "https://e2.bucas.name/#puzzle={}&board_w={}&board_h={}&board_edges={}",
        puzzle_name, puzzle.width, puzzle.height, edges
    )
}

fn score_matched_edges(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let total = (w - 1) * h + w * (h - 1);
    let mut matches = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(piece) = lookup_piece(puzzle, pid) else { continue };
            let e = piece.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 {
                            matches += 1;
                        }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER && e[2] != 0 {
                            matches += 1;
                        }
                    }
                }
            }
        }
    }
    (matches, total)
}

pub fn puzzle_name_from_path(path: &Path) -> String {
    path.file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("puzzle")
        .to_string()
}

// Write the run report. Returns the paths of the written files.
// `extra` is merged into the JSON under a `details` key so each binary can
// attach its own stats (PT swap rates, CP timings, etc.) without this module
// knowing about them.
pub struct RunReport {
    pub json_path: PathBuf,
    pub url_path: PathBuf,
    pub url: String,
}

pub fn write_report(
    output_dir: &Path,
    run_name: &str,
    puzzle: &Puzzle,
    puzzle_name: &str,
    board: &Board,
    extra: Value,
) -> std::io::Result<RunReport> {
    fs::create_dir_all(output_dir)?;

    let (matched, total) = score_matched_edges(puzzle, board);
    let placed = board.cells().iter().filter(|c| c.is_some()).count() as u32;
    let url = bucas_url(puzzle, board, puzzle_name);

    // Per-cell placement: required by downstream plateau analysis so tools
    // don't need to re-derive piece IDs from the bucas board_edges blob.
    let placement: Vec<Value> = board
        .cells()
        .iter()
        .map(|c| match c {
            Some((pid, rot)) => json!({"piece_id": *pid, "rotation": rot.as_u8()}),
            None => Value::Null,
        })
        .collect();

    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let stem = format!("{run_name}_{timestamp}_{matched}of{total}");

    let json_path = output_dir.join(format!("{stem}.json"));
    let url_path = output_dir.join(format!("{stem}.url.txt"));

    let stats = json!({
        "run_name": run_name,
        "timestamp_unix": timestamp,
        "puzzle": {
            "name": puzzle_name,
            "width": puzzle.width,
            "height": puzzle.height,
            "color_count": puzzle.color_count,
            "piece_count": puzzle.pieces().len(),
        },
        "score": {
            "matched_edges": matched,
            "total_edges": total,
            "percent": 100.0 * (matched as f64) / (total as f64),
            "placed_cells": placed,
            "total_cells": puzzle.cell_count(),
        },
        "bucas_url": url,
        "placement": placement,
        "details": extra,
    });

    let mut f = fs::File::create(&json_path)?;
    f.write_all(serde_json::to_string_pretty(&stats)?.as_bytes())?;
    f.write_all(b"\n")?;

    let mut u = fs::File::create(&url_path)?;
    writeln!(u, "{matched}/{total} matched edges  ({:.1}%)", 100.0 * (matched as f64) / (total as f64))?;
    writeln!(u, "{}", url)?;

    Ok(RunReport { json_path, url_path, url })
}
