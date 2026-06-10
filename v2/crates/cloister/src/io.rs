// Output discipline (CLAUDE.md): timestamped run dirs, per-board JSON with
// explicit `pos` fields + .url.txt, and append-only history CSV shared with
// the vol-211 bins (same schema: timestamp,mode,seed,interior_ii,params,
// run_dir,board,bucas_url).

use std::collections::HashMap;
use std::io::Write as _;
use std::path::{Path, PathBuf};

use eternity2_core::{Puzzle, Rotation};

pub const HISTORY: &str = "output/vol-211/cloister_history.csv";

/// UTC YYYYMMDDTHHMMSS — unique-enough run tag without a chrono dep
#[must_use]
pub fn timestamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_secs();
    let days = secs / 86_400;
    let (mut y, mut rem) = (1970u64, days);
    loop {
        let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
        let len = if leap { 366 } else { 365 };
        if rem < len {
            break;
        }
        rem -= len;
        y += 1;
    }
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let ml = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut m = 0;
    while rem >= ml[m] {
        rem -= ml[m];
        m += 1;
    }
    let tod = secs % 86_400;
    format!(
        "{:04}{:02}{:02}T{:02}{:02}{:02}",
        y,
        m + 1,
        rem + 1,
        tod / 3600,
        (tod % 3600) / 60,
        tod % 60
    )
}

/// sparse-pos placement loader (any board JSON in this repo)
pub fn load_placement(path: &Path) -> Result<Vec<(usize, u16, u8)>, String> {
    let txt = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let v: serde_json::Value =
        serde_json::from_str(&txt).map_err(|e| format!("{}: {e}", path.display()))?;
    let arr = v["placement"]
        .as_array()
        .ok_or_else(|| format!("{}: no placement array", path.display()))?;
    let mut out = Vec::with_capacity(arr.len());
    for e in arr {
        out.push((
            e["pos"].as_u64().ok_or("entry without pos")? as usize,
            e["piece_id"].as_u64().ok_or("entry without piece_id")? as u16,
            e["rotation"].as_u64().ok_or("entry without rotation")? as u8,
        ));
    }
    Ok(out)
}

/// bucas URL for any partial 16×16 placement (empty cells = "aaaa")
#[must_use]
pub fn bucas_url(puzzle: &Puzzle, placement: &[(usize, u16, u8)]) -> String {
    let mut at: HashMap<usize, (u16, u8)> = HashMap::new();
    for &(pos, pid, rot) in placement {
        at.insert(pos, (pid, rot));
    }
    let mut edges = String::with_capacity(1024);
    for pos in 0..256 {
        if let Some(&(pid, rot)) = at.get(&pos) {
            let e = puzzle
                .piece(pid)
                .expect("piece")
                .edges
                .rotated(Rotation::from_u8(rot).expect("rot"))
                .as_array();
            for c in e {
                edges.push((b'a' + c) as char);
            }
        } else {
            edges.push_str("aaaa");
        }
    }
    format!("https://e2.bucas.name/#puzzle=Eternity2&board_w=16&board_h=16&board_edges={edges}")
}

/// write a board JSON (+ .url.txt). `meta` = extra JSON fields, already
/// rendered as `"k":v,` pairs (may be empty).
pub fn save_board(
    dir: &Path,
    name: &str,
    puzzle: &Puzzle,
    placement: &[(usize, u16, u8)],
    meta: &str,
) -> PathBuf {
    let mut sorted = placement.to_vec();
    sorted.sort_unstable();
    let url = bucas_url(puzzle, &sorted);
    let body: Vec<String> = sorted
        .iter()
        .map(|&(pos, pid, rot)| {
            format!("{{\"pos\":{pos},\"piece_id\":{pid},\"rotation\":{rot}}}")
        })
        .collect();
    let json = format!(
        "{{{meta}\"bucas_url\":\"{url}\",\"placement\":[{}]}}",
        body.join(",")
    );
    let path = dir.join(name);
    std::fs::write(&path, json).expect("write board");
    std::fs::write(path.with_extension("url.txt"), format!("{url}\n")).expect("write url");
    path
}

/// append a row to the global history CSV (header on first use)
pub fn append_history(
    run_dir: &Path,
    mode: &str,
    seed: u64,
    interior_ii: u32,
    params: &str,
    board: &str,
    url: &str,
) {
    let hist = PathBuf::from(HISTORY);
    if let Some(parent) = hist.parent() {
        std::fs::create_dir_all(parent).expect("history dir");
    }
    let new = !hist.exists();
    let mut f = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&hist)
        .expect("open history");
    if new {
        writeln!(f, "timestamp,mode,seed,interior_ii,params,run_dir,board,bucas_url")
            .expect("hdr");
    }
    writeln!(
        f,
        "{},{},{},{},{},{},{},{}",
        timestamp(),
        mode,
        seed,
        interior_ii,
        params.replace(',', "|"),
        run_dir.display(),
        board,
        url
    )
    .expect("append history");
}

/// interior 14×14 assignment (canonical local pids) -> full-board placement
/// entries at interior positions, using the model's global ids
#[must_use]
pub fn interior_to_placement(
    model: &crate::model::InteriorModel,
    grid: &[(u16, u8)],
) -> Vec<(usize, u16, u8)> {
    let n = model.n;
    grid.iter()
        .enumerate()
        .filter(|&(_, &(p, _))| p != u16::MAX)
        .map(|(cell, &(p, r))| {
            let pos = (cell / n + 1) * 16 + (cell % n + 1);
            (pos, model.global_id[p as usize], r)
        })
        .collect()
}
