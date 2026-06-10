// Vol-211 ground-truth regression: recounts of saved boards. Skips
// gracefully when the data files are not on this machine.

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_cloister::frame;
use eternity2_cloister::io::load_placement;
use eternity2_cloister::model::InteriorModel;
use eternity2_cloister::verify::verify;

fn v2_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn load_e2() -> Option<(eternity2_core::Puzzle, eternity2_core::Hints)> {
    let p = v2_root().join("../data/puzzles/size_16_official_eternity.csv");
    if !p.exists() {
        eprintln!("SKIP: no puzzle csv at {}", p.display());
        return None;
    }
    Some(load_puzzle_with_hints(&p).expect("puzzle"))
}

fn interior_grid(model: &InteriorModel, placement: &[(usize, u16, u8)]) -> Vec<(u16, u8)> {
    let mut g2l = vec![u16::MAX; 256];
    for (l, &g) in model.global_id.iter().enumerate() {
        g2l[g as usize] = l as u16;
    }
    let mut grid = vec![(u16::MAX, 0u8); model.cells];
    for &(pos, pid, rot) in placement {
        if frame::is_ring(pos) {
            continue;
        }
        let (y, x) = (pos / 16, pos % 16);
        grid[(y - 1) * model.n + (x - 1)] = (g2l[pid as usize], rot);
    }
    assert!(grid.iter().all(|&(p, _)| p != u16::MAX), "incomplete interior");
    grid
}

#[test]
fn bucas469_interior_recounts_to_358() {
    let Some((puzzle, hints)) = load_e2() else { return };
    let path = v2_root().join("output/vol-211/bucas469_interior_only.json");
    if !path.exists() {
        eprintln!("SKIP: {} missing", path.display());
        return;
    }
    let model = InteriorModel::from_puzzle(&puzzle, &hints);
    let placement = load_placement(&path).expect("board");
    let grid = interior_grid(&model, &placement);
    assert_eq!(model.ii_matches(&grid), 358);
}

#[test]
fn vol211_complete_ii356_recounts() {
    let Some((puzzle, hints)) = load_e2() else { return };
    let model = InteriorModel::from_puzzle(&puzzle, &hints);
    // any COMPLETE_II356 board from the vol-211 runs
    let pattern = v2_root().join("output/vol-211");
    let Ok(dirs) = std::fs::read_dir(&pattern) else { return };
    let mut found = false;
    for d in dirs.flatten() {
        let p = d.path();
        if !p.is_dir() {
            continue;
        }
        let Ok(files) = std::fs::read_dir(&p) else { continue };
        for f in files.flatten() {
            let name = f.file_name().to_string_lossy().into_owned();
            if name.starts_with("COMPLETE_II356") && name.ends_with(".json") {
                let placement = load_placement(&f.path()).expect("board");
                let grid = interior_grid(&model, &placement);
                assert_eq!(model.ii_matches(&grid), 356, "{name}");
                found = true;
            }
        }
    }
    if !found {
        eprintln!("SKIP: no COMPLETE_II356 boards found");
    }
}

#[test]
fn community_strict_460_verifies() {
    let Some((puzzle, hints)) = load_e2() else { return };
    let root = v2_root().join("output/vol-211");
    let Ok(dirs) = std::fs::read_dir(&root) else { return };
    let mut found = false;
    for d in dirs.flatten() {
        let p = d.path();
        if !p.file_name().is_some_and(|n| n.to_string_lossy().starts_with("corpus_decoded")) {
            continue;
        }
        for name in ["groups_219671623_460.json", "groups_219328931_460.json"] {
            let f = p.join(name);
            if !f.exists() {
                continue;
            }
            let placement = load_placement(&f).expect("board");
            let chk = verify(&puzzle, &hints, &placement);
            assert!(chk.is_legal_complete(), "{name}: {chk:?}");
            assert_eq!(chk.total(), 460, "{name}");
            assert_eq!((chk.ii, chk.ib, chk.bb), (350, 50, 60), "{name}");
            assert_eq!(chk.hints_ok, 5, "{name} strict");
            // its border must load as a legal BB=60 frame
            let fr = frame::load(&f, &puzzle).expect("frame");
            assert_eq!(fr.bb, 60, "{name} frame");
            assert_eq!(InteriorModel::ib_max(&fr.targets), 56);
            found = true;
        }
    }
    if !found {
        eprintln!("SKIP: no decoded strict-460 boards found");
    }
}

#[test]
fn vol76_frame_loads_bb60() {
    let Some((puzzle, _)) = load_e2() else { return };
    let f = v2_root().join("output/vol-76/frame_solution_0.json");
    if !f.exists() {
        eprintln!("SKIP: {} missing", f.display());
        return;
    }
    let fr = frame::load(&f, &puzzle).expect("frame");
    assert_eq!(fr.bb, 60);
    assert_eq!(InteriorModel::ib_max(&fr.targets), 56);
}
