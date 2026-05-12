// Vol-17 NOVEL OUTSIDE-THE-BOX — MaxSAT-based cluster repair.
//
// E6/E7 proved that the 455 board's cluster is UNSAT under exact-match
// CP (gacolor_ac3 wipes instantly). But MaxSAT can find the OPTIMAL
// assignment that maximizes matched edges even if no clean completion
// exists. So we encode the cluster as MaxSAT (hard: piece-uniqueness +
// cell-assignment; soft: edge-match-aux vars per interior edge) and
// hand to z3 -wcnf or kissat.
//
// First MaxSAT-as-ALNS-repair on Eternity II (I think).
//
// Pipeline:
//   1. Load board.
//   2. Find mismatch cluster + halo.
//   3. Build PinnedMap = all cells outside cluster.
//   4. Encode MaxSAT via eternity2-sat-encoder.
//   5. Write WCNF to disk.
//   6. Shell out to z3 -wcnf with timeout.
//   7. Parse model lines (v +x -y ...).
//   8. Decode back to board placements.
//   9. Verify + score + save.
//
// CLI:
//   cluster_maxsat_repair --board PATH [--halo 1] [--solver z3|kissat]
//                         [--timeout-s 120]

#![forbid(unsafe_code)]

use std::collections::{BTreeSet, HashMap};
use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Hints, Rotation};
use eternity2_localsearch::find_mismatches;
use eternity2_sat_encoder::{encode_with_pinned, write_wcnf_old, EncodeOptions, PinnedMap, VarMap};

fn load_board(path: &std::path::Path) -> Board {
    let raw = std::fs::read_to_string(path).expect("read");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let mut b = Board::empty(&puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for p in arr {
            if p.is_null() { continue; }
            let pos = p["pos"].as_u64().unwrap() as u32;
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot = Rotation::from_u8(p["rotation"].as_u64().unwrap() as u8).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut halo: u32 = 1;
    let mut solver = "z3".to_string();
    let mut timeout_s: u32 = 120;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--halo" => halo = args.next().unwrap().parse().unwrap(),
            "--solver" => solver = args.next().unwrap(),
            "--timeout-s" => timeout_s = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("--board required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path);
    let (m0, _) = score_board(&puzzle, &board);
    let p0 = placed_count(&board, &puzzle);
    eprintln!("loaded board: {p0} placed, {m0}/480 matched");

    // Find cluster cells + halo.
    let w = puzzle.width;
    let h = puzzle.height;
    let mismatches = find_mismatches(&puzzle, &board);
    let mut mismatch_cells: BTreeSet<u32> = BTreeSet::new();
    for m in &mismatches {
        mismatch_cells.insert(m.cell_a);
        mismatch_cells.insert(m.cell_b);
    }
    let mut free: BTreeSet<u32> = mismatch_cells.clone();
    for _ in 0..halo {
        let snap: Vec<u32> = free.iter().copied().collect();
        for p in snap {
            let x = p % w; let y = p / w;
            if x + 1 < w { free.insert(p + 1); }
            if x > 0 { free.insert(p - 1); }
            if y + 1 < h { free.insert(p + w); }
            if y > 0 { free.insert(p - w); }
        }
    }
    // Don't free canonical hints.
    for h in &hints.hints {
        free.remove(&h.position);
    }
    eprintln!("cluster cells: {}, halo={halo} → free: {}", mismatch_cells.len(), free.len());

    // Build PinnedMap = cells NOT in free.
    let pieces_arr = puzzle.pieces();
    let mut pinned: PinnedMap = PinnedMap::new();
    for pos in 0..puzzle.cell_count() {
        if free.contains(&pos) { continue; }
        if let Some((pid, rot)) = board.get(pos) {
            if let Some(pi) = pieces_arr.iter().position(|p| p.id == pid) {
                pinned.insert(pos, (pi as u32, rot));
            }
        }
    }
    eprintln!("pinned cells (constants): {}", pinned.len());

    // Build VarMap + encode MaxSAT.
    eprintln!("building VarMap...");
    let t0 = Instant::now();
    let vmap = VarMap::build_with_pinned(&puzzle, &pinned);
    eprintln!("  VarMap built in {:.2}s: {} piece-vars, {} edges, {} total vars",
        t0.elapsed().as_secs_f64(),
        vmap.var_to_cpr.len(), vmap.edges.len(), vmap.n_vars);

    let t1 = Instant::now();
    let cnf = encode_with_pinned(&puzzle, &hints, &vmap,
        &EncodeOptions { soft_edge_match: true }, &pinned);
    eprintln!("  encoded MaxSAT in {:.2}s: {} hard, {} soft",
        t1.elapsed().as_secs_f64(), cnf.clauses.len(), cnf.soft_clauses.len());

    // Write WCNF (old format for z3 -wcnf).
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from("output/v17_cluster_maxsat");
    let _ = std::fs::create_dir_all(&out_dir);
    let wcnf_path = out_dir.join(format!("cluster_{run_id}.wcnf"));
    let wcnf_str = write_wcnf_old(&cnf);
    std::fs::write(&wcnf_path, &wcnf_str).expect("write wcnf");
    eprintln!("WCNF: {} ({} MB)", wcnf_path.display(),
        wcnf_str.len() as f64 / 1_048_576.0);

    // Shell out to MaxSAT solver.
    eprintln!("\nInvoking solver: {solver} (timeout {}s)...", timeout_s);
    let t_solve = Instant::now();
    let output = match solver.as_str() {
        "z3" => Command::new("z3")
            .args(["-wcnf", &format!("-T:{timeout_s}"), wcnf_path.to_str().unwrap()])
            .output(),
        "kissat" => Command::new("kissat")
            .args([&format!("--time={timeout_s}"), wcnf_path.to_str().unwrap()])
            .output(),
        other => panic!("unknown --solver {other}"),
    };
    let output = match output {
        Ok(o) => o,
        Err(e) => { eprintln!("solver invocation failed: {e}"); std::process::exit(2); }
    };
    let elapsed = t_solve.elapsed();
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    eprintln!("solver elapsed: {:.1}s", elapsed.as_secs_f64());
    // Save stdout for inspection.
    let solver_log = out_dir.join(format!("cluster_{run_id}_{solver}.log"));
    let _ = std::fs::write(&solver_log,
        format!("=== STDOUT ===\n{stdout}\n=== STDERR ===\n{stderr}\n"));
    eprintln!("solver log: {}", solver_log.display());

    // Parse model. z3/kissat output:
    //   s OPTIMUM FOUND / s SATISFIABLE / s UNSATISFIABLE / s UNKNOWN
    //   v <literals separated by spaces>
    //   ...
    let mut status = "UNKNOWN".to_string();
    let mut model: HashMap<u32, bool> = HashMap::new();
    for line in stdout.lines() {
        let line = line.trim();
        if line.starts_with("s ") {
            status = line[2..].trim().to_string();
        } else if line.starts_with("v ") {
            for tok in line[2..].split_whitespace() {
                if let Ok(lit) = tok.parse::<i64>() {
                    let var = lit.unsigned_abs() as u32;
                    if var == 0 { break; } // DIMACS terminator.
                    model.insert(var, lit > 0);
                }
            }
        }
    }
    eprintln!("solver status: {status}");
    eprintln!("model vars: {}", model.len());

    if status != "OPTIMUM FOUND" && status != "SATISFIABLE" && status != "OPT" {
        eprintln!("WARNING: solver did not find SAT/OPT (got {status:?}). Returning input.");
        return;
    }

    // Decode model: for each piece-var with positive assignment, place
    // that piece at that cell with that rotation.
    let mut new_board = board.clone();
    // First, clear all free cells (in case the model places different pieces).
    // We'll reconstruct from model.
    for &pos in &free {
        // remove placement at pos
        // No direct "unset" in Board; emulate by re-placing pinned cells.
    }
    // Strategy: build a fresh Board, fill in pinned cells, then fill in
    // model-derived free cells.
    let mut new_board = Board::empty(&puzzle);
    for (&pos, &(pi, rot)) in &pinned {
        let pid = pieces_arr[pi as usize].id;
        new_board.place(pos, pid, rot);
    }
    let mut n_placed = 0u32;
    for (vi, &(pos, pi, rot)) in vmap.var_to_cpr.iter().enumerate() {
        let var = (vi as u32) + 1;
        if model.get(&var).copied() == Some(true) {
            let pid = pieces_arr[pi as usize].id;
            new_board.place(pos, pid, rot);
            n_placed += 1;
        }
    }
    eprintln!("placed {} pieces from model (free region size: {})", n_placed, free.len());

    let (m_new, _) = score_board(&puzzle, &new_board);
    let p_new = placed_count(&new_board, &puzzle);
    let url = bucas_url(&puzzle, &new_board, "v17_cluster_maxsat");
    eprintln!(
        "\nResult: matched={m_new}/480 (was {m0}, Δ={:+}) placed={p_new}/256",
        m_new as i32 - m0 as i32
    );
    eprintln!("bucas: {url}");

    let json = serde_json::json!({
        "matched_in": m0, "matched_out": m_new, "delta": m_new as i32 - m0 as i32,
        "solver": solver, "halo": halo, "timeout_s": timeout_s,
        "free_size": free.len(), "status": status,
        "elapsed_solver_s": elapsed.as_secs_f64(),
        "bucas_url": url,
        "placement": (0..puzzle.cell_count()).map(|p| {
            new_board.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let json_path = out_dir.join(format!("cluster_{run_id}_result.json"));
    let _ = std::fs::write(&json_path, serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: {}", json_path.display());
}
