//! Vol-27 — in-process ONNX inference for `ValueOrder::Learned`.
//!
//! Replaces vol-26's stdio Python bridge. Loads an ONNX model at solver
//! construction (path from env var `E2_LEARNED_MODEL`, default
//! `ml/runs/v1/model.onnx`) and runs inference via the `ort` crate.
//!
//! Inference cost on M1: ~0.1 ms per call (vs vol-26's ~15 ms stdio
//! round-trip), so the 540× algorithmic win from vol-26 finally surfaces
//! as a wall-clock win. If the model file is missing or the session
//! fails to build, the scorer reports unavailable and the engine falls
//! back to insertion order — preserves correctness for tests.

#![cfg(not(target_arch = "wasm32"))]

use std::path::PathBuf;
use std::sync::Mutex;

use ndarray::{Array1, Array3};
use ort::session::Session;
use ort::value::Tensor;

pub struct LearnedScorer {
    session: Mutex<Session>,
    /// Cached size of the puzzle the model was trained on. The scorer
    /// only emits scores when the puzzle has this size; other sizes
    /// trigger the silent fallback (the model is grid-size-specific).
    grid_size: usize,
    /// Number of pieces the model knows about. Used to validate that
    /// candidate `piece_id`s are in-range before computing action
    /// indices.
    n_pieces: u32,
}

impl LearnedScorer {
    pub fn spawn() -> Option<Self> {
        let path = std::env::var("E2_LEARNED_MODEL")
            .unwrap_or_else(|_| "ml/runs/v1/model.onnx".to_string());
        Self::from_path(&path)
    }

    fn from_path(path: &str) -> Option<Self> {
        let p = PathBuf::from(path);
        if !p.exists() {
            return None;
        }
        let session = Session::builder().ok()?.commit_from_file(&p).ok()?;

        // Heuristic: derive (grid_size, n_pieces) from the trained model
        // metadata if present; otherwise default to the 6×6/5c vol-26
        // configuration. We could ship sidecar JSON but for the gate this
        // is sufficient.
        let (grid_size, n_pieces) = read_grid_meta(path).unwrap_or((6, 36));
        Some(Self {
            session: Mutex::new(session),
            grid_size,
            n_pieces,
        })
    }

    /// Score each candidate `(piece_id, rotation)` at `target_pos` given
    /// per-cell features. Returns one score per candidate or `None` if
    /// the puzzle size doesn't match the model or inference fails.
    pub fn score(
        &self,
        feats: &Array3<f32>,
        target_pos: u32,
        candidates: &[(u16, u8)],
    ) -> Option<Vec<f32>> {
        let n_cells = self.grid_size * self.grid_size;
        // Validate feature shape: (1, n_cells, 13).
        if feats.shape() != [1, n_cells, 13] {
            return None;
        }

        let mut sess = self.session.lock().ok()?;
        let feats_t = Tensor::from_array(feats.clone()).ok()?;
        let tp_arr = Array1::from_vec(vec![i64::from(target_pos)]);
        let tp_t = Tensor::from_array(tp_arr).ok()?;
        let outputs = sess
            .run(ort::inputs![
                "feats" => feats_t,
                "target_pos" => tp_t,
            ])
            .ok()?;

        // Extract logits: shape (1, n_actions) where n_actions = n_pieces * 4.
        let (shape, data) = outputs[0].try_extract_tensor::<f32>().ok()?;
        // Expect rank 2.
        if shape.len() != 2 || shape[0] != 1 {
            return None;
        }
        let n_actions = shape[1] as usize;
        if n_actions != self.n_pieces as usize * 4 {
            return None;
        }

        // Look up the score for each candidate via flat action index.
        let mut scores = Vec::with_capacity(candidates.len());
        for &(pid, rot) in candidates {
            if u32::from(pid) >= self.n_pieces || rot >= 4 {
                scores.push(f32::NEG_INFINITY);
                continue;
            }
            let action = usize::from(pid) * 4 + usize::from(rot);
            scores.push(data[action]);
        }
        Some(scores)
    }

    pub fn grid_size(&self) -> usize {
        self.grid_size
    }
}

/// Read the (grid_size, n_pieces) tuple from a sidecar `.meta.json` next
/// to the model file, if present. Format:
/// `{"size": 6, "n_pieces": 36}`. Falls back to defaults when missing.
fn read_grid_meta(model_path: &str) -> Option<(usize, u32)> {
    let meta_path = format!("{model_path}.meta.json");
    let raw = std::fs::read_to_string(&meta_path).ok()?;
    #[derive(serde::Deserialize)]
    struct Meta {
        size: usize,
        n_pieces: u32,
    }
    let m: Meta = serde_json::from_str(&raw).ok()?;
    Some((m.size, m.n_pieces))
}
