// attach2 — exact border attach for an interior board (vol-211 MIP, in
// the clean crate). Usage: attach2 <interior.json> [--time-limit-secs N]
// [--require-bb60] [--out-dir D]

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_cloister::border::{attach, AttachOpts};
use eternity2_cloister::io as cio;
use eternity2_cloister::verify;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let get = |flag: &str| -> Option<String> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1).cloned())
    };
    let path = args
        .first()
        .filter(|a| !a.starts_with("--"))
        .expect("usage: attach2 <interior.json>")
        .clone();
    let opts = AttachOpts {
        time_limit_secs: get("--time-limit-secs").and_then(|s| s.parse().ok()).unwrap_or(120.0),
        require_bb60: args.iter().any(|a| a == "--require-bb60"),
    };
    let puzzle_path = PathBuf::from(
        get("--puzzle").unwrap_or_else(|| "../data/puzzles/size_16_official_eternity.csv".into()),
    );
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let interior = cio::load_placement(&PathBuf::from(&path)).expect("interior board");

    eprintln!("solving border-attach MIP (limit {}s)...", opts.time_limit_secs);
    let res = attach(&puzzle, &interior, &opts).expect("attach");
    let chk = verify::verify(&puzzle, &hints, &res.placement);
    assert!(chk.is_legal_complete(), "attached board must be legal: {chk:?}");
    println!(
        "attach: obj={:.1} -> II={}/364 IB={}/56 BB={}/60 TOTAL={}/480 hints {}/{}",
        res.obj,
        chk.ii,
        chk.ib,
        chk.bb,
        chk.total(),
        chk.hints_ok,
        chk.hints_total
    );

    let out_dir = PathBuf::from(
        get("--out-dir").unwrap_or_else(|| format!("output/vol-212/attach2_{}", cio::timestamp())),
    );
    std::fs::create_dir_all(&out_dir).expect("mkdir");
    let stem = PathBuf::from(&path)
        .file_stem()
        .map_or_else(|| "interior".into(), |s| s.to_string_lossy().into_owned());
    let name = format!("ATTACHED_{}_{stem}.json", chk.total());
    let meta = format!(
        "\"matched\":{},\"ii\":{},\"ib\":{},\"bb\":{},\"hints_ok\":{},\"source\":\"attach2:{path}\",",
        chk.total(),
        chk.ii,
        chk.ib,
        chk.bb,
        chk.hints_ok
    );
    let saved = cio::save_board(&out_dir, &name, &puzzle, &res.placement, &meta);
    println!("saved {}", saved.display());
    cio::append_history(
        &out_dir,
        "attach2",
        0,
        chk.ii,
        &format!(
            "total={};ib={};bb={};bb60={}",
            chk.total(),
            chk.ib,
            chk.bb,
            opts.require_bb60
        ),
        &saved.display().to_string(),
        &cio::bucas_url(&puzzle, &res.placement),
    );
}
