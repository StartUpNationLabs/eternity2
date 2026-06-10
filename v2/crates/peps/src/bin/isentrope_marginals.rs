// ISENTROPE marginals (vol-209 #2) — per-cell placement marginals at the TRUE 16×16
// board via the environment method (all cells in O(size) sweeps). A peaked marginal
// = a near-forced placement (a soft refinement of LATTICE's "zero forced placements").
//
// Usage: isentrope_marginals --chi 8 [--puzzle <csv>] [--cells 0,15,..] [--top 8]
//        --validate  (cross-check cell 0 against slow exact pinning on the puzzle)

use std::sync::Arc;
use std::collections::HashMap;
use eternity2_peps::{PepsContext, mps_proper::{cell_marginals, log_z_mps_cells}};
use eternity2_peps::tensor::build_all_cell_tensors;
use eternity2_puzzle_io::load_puzzle;

fn sig_to_piece(ctx: &PepsContext, sig: [u8; 4]) -> Option<(u16, u8)> {
    ctx.signature_lookup.get(&sig).and_then(|v| v.first().copied())
}

fn main() {
    let mut chi = 8usize;
    let mut puzzle_path = "../data/puzzles/size_16_official_eternity.csv".to_string();
    let mut cells_arg: Vec<usize> = vec![]; // empty => report summary for all cells
    let mut top = 6usize;
    let mut validate = false;
    let mut pin_board: Option<String> = None; // JSON board to pin a prefix of
    let mut pin_rows: usize = 0;              // pin the top N rows from pin_board
    let mut pin_shuffle = false;              // pin the SAME pieces but at shuffled positions (control)
    let mut dump_path: Option<String> = None; // dump per-cell per-placement probs
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--chi" => { chi = args[i + 1].parse().unwrap(); i += 2; }
            "--puzzle" => { puzzle_path = args[i + 1].clone(); i += 2; }
            "--cells" => { cells_arg = args[i + 1].split(',').map(|s| s.parse().unwrap()).collect(); i += 2; }
            "--top" => { top = args[i + 1].parse().unwrap(); i += 2; }
            "--validate" => { validate = true; i += 1; }
            "--pin-board" => { pin_board = Some(args[i + 1].clone()); i += 2; }
            "--pin-rows" => { pin_rows = args[i + 1].parse().unwrap(); i += 2; }
            "--pin-shuffle" => { pin_shuffle = true; i += 1; }
            "--dump" => { dump_path = Some(args[i + 1].clone()); i += 2; }
            _ => { i += 1; }
        }
    }
    let puzzle = load_puzzle(std::path::Path::new(&puzzle_path)).expect("load");
    let size = puzzle.width as usize;
    let ctx = PepsContext::new(Arc::new(puzzle));
    let mu = vec![0.0f64; ctx.n_pieces];

    // build pin set from a board prefix (top pin_rows rows), if requested.
    let mut pinned: Vec<Option<(u16, u8)>> = vec![None; size * size];
    let mut pinned_positions: Vec<usize> = Vec::new();
    if let Some(bp) = &pin_board {
        let raw = std::fs::read_to_string(bp).expect("read pin board");
        let v: serde_json::Value = serde_json::from_str(&raw).expect("parse board");
        let pl = v.get("placement").and_then(|p| p.as_array()).expect("placement");
        // collect (pos, pid, rot) for the top pin_rows rows
        let mut entries: Vec<(usize, u16, u8)> = Vec::new();
        for (idx, e) in pl.iter().enumerate() {
            if e.is_null() { continue; }
            let pos = e.get("pos").and_then(|x| x.as_u64()).map(|x| x as usize).unwrap_or(idx);
            let pid = e.get("piece_id").and_then(|x| x.as_u64()).expect("piece_id") as u16;
            let rot = e.get("rotation").and_then(|x| x.as_u64()).unwrap_or(0) as u8;
            if pos / size < pin_rows { entries.push((pos, pid, rot)); }
        }
        if pin_shuffle {
            // control: keep the SAME (pid,rot) multiset but assign to the same positions
            // in a rotated order — breaks the spatial correctness while keeping the pool.
            let n = entries.len();
            let prs: Vec<(u16, u8)> = entries.iter().map(|&(_, p, r)| (p, r)).collect();
            for (j, &(pos, _, _)) in entries.iter().enumerate() {
                let (p, r) = prs[(j + n / 2) % n]; // rotate the assignment
                pinned[pos] = Some((p, r));
                pinned_positions.push(pos);
            }
        } else {
            for &(pos, pid, rot) in &entries {
                pinned[pos] = Some((pid, rot));
                pinned_positions.push(pos);
            }
        }
        eprintln!("[pin] pinned {} cells (top {} rows){}", pinned_positions.len(), pin_rows,
                  if pin_shuffle { " [SHUFFLED control]" } else { "" });
    }
    let base = build_all_cell_tensors(&ctx, &mu, &pinned);

    eprintln!("[init] size={size} K={} chi={chi}", ctx.k_colors);
    let t0 = std::time::Instant::now();
    let marg = cell_marginals(&ctx, &base, chi);
    eprintln!("[marg] all {} cells in {:.2}s", size * size, t0.elapsed().as_secs_f64());

    // normalize each cell's marginal -> probabilities; compute entropy + effective #.
    println!("cell,row,col,nplace,entropy_nats,n_eff,top_piece,top_prob");
    let report_cells: Vec<usize> = if cells_arg.is_empty() { (0..size * size).collect() } else { cells_arg.clone() };
    for &c in &report_cells {
        let m = &marg[c];
        let tot: f64 = m.values().sum();
        if tot <= 0.0 { println!("{c},{},{},0,0,0,,0", c / size, c % size); continue; }
        let mut probs: Vec<([u8;4], f64)> = m.iter().map(|(&s, &w)| (s, w / tot)).collect();
        probs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        let ent: f64 = probs.iter().filter(|&&(_, p)| p > 0.0).map(|&(_, p)| -p * p.ln()).sum();
        let n_eff = ent.exp();
        let (tp, tprob) = probs.first().map(|&(s, p)| (sig_to_piece(&ctx, s).map(|x| x.0).unwrap_or(9999), p)).unwrap_or((9999, 0.0));
        println!("{c},{},{},{},{:.4},{:.2},{},{:.4}", c / size, c % size, probs.len(), ent, n_eff, tp, tprob);
        if !cells_arg.is_empty() {
            eprintln!("  cell {c} (r{} c{}): entropy {ent:.3} nats, n_eff {n_eff:.1} of {}", c / size, c % size, probs.len());
            for &(s, p) in probs.iter().take(top) {
                if let Some((pid, rot)) = sig_to_piece(&ctx, s) {
                    eprintln!("    piece {pid:3} rot {rot}: P={p:.4}  sig={s:?}");
                }
            }
        }
    }
    // DUMP per-cell per-placement probabilities (for marginal-guided completion).
    if let Some(dp) = &dump_path {
        use std::io::Write;
        let mut f = std::fs::File::create(dp).expect("create dump");
        writeln!(f, "cell,piece,rot,prob").unwrap();
        for c in 0..size * size {
            let m = &marg[c];
            let tot: f64 = m.values().sum();
            if tot <= 0.0 { continue; }
            for (&s, &w) in m.iter() {
                if let Some((pid, rot)) = sig_to_piece(&ctx, s) {
                    writeln!(f, "{},{},{},{:.6e}", c, pid, rot, w / tot).unwrap();
                }
            }
        }
        eprintln!("[dump] wrote per-cell placement probs to {dp}");
    }
    // FREE-TAIL summary (conditional marginals): mean n_eff over UNPINNED cells.
    {
        let pinset: std::collections::HashSet<usize> = pinned_positions.iter().copied().collect();
        let mut neff_free: Vec<f64> = Vec::new();
        let mut neff_free_int: Vec<f64> = Vec::new();
        for c in 0..size * size {
            if pinset.contains(&c) { continue; }
            let m = &marg[c];
            let tot: f64 = m.values().sum();
            if tot <= 0.0 { continue; }
            let ent: f64 = m.values().map(|&w| { let p = w / tot; if p > 0.0 { -p * p.ln() } else { 0.0 } }).sum();
            let ne = ent.exp();
            neff_free.push(ne);
            let (r, cc) = (c / size, c % size);
            if r != 0 && r != size - 1 && cc != 0 && cc != size - 1 { neff_free_int.push(ne); }
        }
        let mean = |v: &Vec<f64>| if v.is_empty() { 0.0 } else { v.iter().sum::<f64>() / v.len() as f64 };
        let mut s = neff_free.clone(); s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        eprintln!("[FREE-TAIL] pinned={} free={} | free n_eff: mean {:.1}, min {:.2}, median {:.1}, max {:.1}",
                  pinned_positions.len(), neff_free.len(), mean(&neff_free),
                  s.first().copied().unwrap_or(0.0), s.get(s.len()/2).copied().unwrap_or(0.0), s.last().copied().unwrap_or(0.0));
        eprintln!("[FREE-INTERIOR] mean n_eff = {:.1} (of {} free interior cells)", mean(&neff_free_int), neff_free_int.len());
        println!("# SUMMARY pin_rows={} pinned={} free_mean_neff={:.2} free_interior_mean_neff={:.2}",
                 pin_rows, pinned_positions.len(), mean(&neff_free), mean(&neff_free_int));
    }

    if validate {
        // slow exact pinning of cell 0, compare to environment marginal.
        eprintln!("=== VALIDATION: exact pinning of cell 0 vs environment ===");
        let log_z_full = log_z_mps_cells(&ctx, &base, chi);
        let mut pin_probs: HashMap<(u16,u8), f64> = HashMap::new();
        let mut logs: Vec<((u16,u8), f64)> = Vec::new();
        for pid in 0..ctx.n_pieces as u16 {
            for rot in 0..4u8 {
                let mut pinned = vec![None; size * size];
                pinned[0] = Some((pid, rot));
                let cells = build_all_cell_tensors(&ctx, &mu, &pinned);
                let lz = log_z_mps_cells(&ctx, &cells, chi);
                if lz.is_finite() { logs.push(((pid,rot), lz)); }
            }
        }
        let maxl = logs.iter().map(|&(_,l)| l).fold(f64::NEG_INFINITY, f64::max);
        let sum: f64 = logs.iter().map(|&(_,l)| (l-maxl).exp()).sum();
        for &((pid,rot), l) in &logs { pin_probs.insert((pid,rot), (l-maxl).exp()/sum); }
        // environment cell-0 probs (by piece)
        let m = &marg[0]; let tot: f64 = m.values().sum();
        let mut env_probs: HashMap<(u16,u8), f64> = HashMap::new();
        for (&s,&w) in m { if let Some(pr)=sig_to_piece(&ctx,s){ env_probs.insert(pr, w/tot);} }
        // compare top entries
        let mut keys: Vec<_> = pin_probs.keys().chain(env_probs.keys()).copied().collect();
        keys.sort(); keys.dedup();
        keys.sort_by(|a,b| pin_probs.get(b).unwrap_or(&0.0).partial_cmp(pin_probs.get(a).unwrap_or(&0.0)).unwrap());
        let mut maxerr = 0.0f64;
        eprintln!("  (pid,rot)  pin_P    env_P");
        for k in keys.iter().take(8) {
            let pp = *pin_probs.get(k).unwrap_or(&0.0); let ep = *env_probs.get(k).unwrap_or(&0.0);
            eprintln!("  {:?}  {:.4}  {:.4}", k, pp, ep);
            maxerr = maxerr.max((pp-ep).abs());
        }
        eprintln!("  MAX |pin - env| over top entries = {maxerr:.5}  => {}", if maxerr < 0.01 {"ENV VALIDATED"} else {"MISMATCH"});
    }
}
