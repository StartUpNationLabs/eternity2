//! Vol-26 — Rust↔Python stdio bridge for `ValueOrder::Learned`.
//!
//! Spawns a Python subprocess (path read from the env var `E2_BRIDGE_CMD`,
//! default `uv run python ml/infer_bridge.py`). The protocol is line-based
//! JSON:
//!   request:  {"feats": [[...]], "target_pos": u32, "candidates": [[piece_id, rotation]]}
//!   response: {"scores": [f32]}  // one score per candidate, higher = better
//!
//! One subprocess per `EngineSolver`. The subprocess is auto-killed on
//! drop. If startup fails (e.g., Python not installed, model file missing)
//! the bridge silently disables and `ValueOrder::Learned` falls back to
//! `InsertionOrder` so the engine remains correct.

#![cfg(not(target_arch = "wasm32"))]

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};

pub struct LearnedBridge {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
    line_buf: String,
}

impl LearnedBridge {
    /// Spawn the inference subprocess. Returns `None` if startup fails so
    /// the caller can fall back to insertion order.
    pub fn spawn() -> Option<Self> {
        let cmd = std::env::var("E2_BRIDGE_CMD")
            .unwrap_or_else(|_| "uv run python ml/infer_bridge.py".to_string());
        let mut parts = cmd.split_whitespace();
        let prog = parts.next()?;
        let args: Vec<&str> = parts.collect();
        let cwd = std::env::var("E2_BRIDGE_CWD").ok();

        let mut command = Command::new(prog);
        command
            .args(&args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit());
        if let Some(dir) = cwd {
            command.current_dir(dir);
        }
        let mut child = command.spawn().ok()?;
        let stdin = child.stdin.take()?;
        let stdout = BufReader::new(child.stdout.take()?);

        let mut br = Self {
            child,
            stdin,
            stdout,
            line_buf: String::with_capacity(8 * 1024),
        };

        // Wait for the "ready" handshake. Bound retries so we don't hang
        // forever on a misconfigured bridge.
        for _ in 0..3 {
            br.line_buf.clear();
            if br.stdout.read_line(&mut br.line_buf).ok()? > 0
                && br.line_buf.trim_end().starts_with("{\"ready\"")
            {
                return Some(br);
            }
        }
        None
    }

    /// Send a scoring request. Returns one score per candidate or `None`
    /// on any I/O failure; the caller falls back to insertion order.
    pub fn score(
        &mut self,
        feats: &str,
        target_pos: u32,
        candidates: &str,
    ) -> Option<Vec<f32>> {
        // Compose request line. We accept pre-serialized JSON fragments
        // for `feats` and `candidates` to avoid double-allocation in the
        // hot loop (the engine has these as native types and converts to
        // strings via `serde_json::to_string`).
        let req = format!(
            "{{\"feats\":{feats},\"target_pos\":{target_pos},\"candidates\":{candidates}}}\n"
        );
        self.stdin.write_all(req.as_bytes()).ok()?;
        self.stdin.flush().ok()?;

        self.line_buf.clear();
        if self.stdout.read_line(&mut self.line_buf).ok()? == 0 {
            return None;
        }

        // Parse the response. Tiny structure so use the simplest path.
        #[derive(serde::Deserialize)]
        struct Resp {
            scores: Vec<f32>,
        }
        let parsed: Resp = serde_json::from_str(self.line_buf.trim_end()).ok()?;
        Some(parsed.scores)
    }
}

impl Drop for LearnedBridge {
    fn drop(&mut self) {
        // Close stdin so the subprocess sees EOF, then kill if it doesn't
        // exit on its own.
        let _ = self.stdin.write_all(b"{\"shutdown\":true}\n");
        let _ = self.stdin.flush();
        // Don't wait forever; kill is fine.
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
