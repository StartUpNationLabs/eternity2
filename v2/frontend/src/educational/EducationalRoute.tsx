// Educational mode — WASM in-browser solve.
// This is the first user-visible v2 thing (V2_DESIGN.md migration step 4).
// More routes (tutorial, path play, glossary) are planned; for now the
// landing surface lets users generate a small puzzle and watch naive
// solve it offline.

import { useState } from "react";
import { Board, type PiecePlacement } from "../lib/Board";

interface WasmModule {
  generatePuzzle: (input: { size: number; interior_colors: number; seed: number | bigint }) => {
    width: number;
    height: number;
    color_count: number;
    pieces: Array<{ id: number; edges: [number, number, number, number] }>;
    fingerprint: bigint;
  };
  solveNaive: (input: {
    puzzle: { width: number; height: number; color_count: number; pieces: Array<{ id: number; edges: [number, number, number, number] }> };
    traversal: "row_by_row" | "spiral";
    time_budget_ms: number | bigint;
    all_solutions: boolean;
  }) => {
    outcome: "solved" | "exhausted" | "timed_out" | "error";
    board?: Array<{ position: number; piece_id: number; rotation: number }>;
    message?: string;
    events?: Array<{ node_id: bigint; depth: number; timestamp_us: bigint; kind: string }>;
  };
}

async function loadWasm(): Promise<WasmModule> {
  // The wasm bundle is built by `v2/wasm/build.sh` and served from
  // `/wasm/pkg/`. In dev we copy it into the public dir; in prod the
  // Dockerfile copies it next to the static assets.
  const init = (await import(/* @vite-ignore */ "@wasm/eternity2_wasm.js")) as {
    default: (input?: { module_or_path?: string }) => Promise<unknown>;
  } & WasmModule;
  await init.default({ module_or_path: "/wasm/pkg/eternity2_wasm_bg.wasm" });
  return init;
}

export function EducationalRoute() {
  const [size, setSize] = useState(4);
  const [colors, setColors] = useState(4);
  const [seed, setSeed] = useState(7);
  const [traversal, setTraversal] = useState<"row_by_row" | "spiral">("row_by_row");
  const [board, setBoard] = useState<PiecePlacement[]>([]);
  const [width, setWidth] = useState(4);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string>("");

  async function run() {
    setRunning(true);
    setStatus("loading wasm...");
    try {
      const mod = await loadWasm();
      setStatus("generating...");
      const puzzle = mod.generatePuzzle({ size, interior_colors: colors, seed });
      setWidth(puzzle.width);
      setStatus("solving...");
      const result = mod.solveNaive({
        puzzle: {
          width: puzzle.width,
          height: puzzle.height,
          color_count: puzzle.color_count,
          pieces: puzzle.pieces,
        },
        traversal,
        time_budget_ms: 10_000,
        all_solutions: false,
      });
      if (result.outcome === "solved" && result.board) {
        const byId = new Map(puzzle.pieces.map((p) => [p.id, p.edges]));
        setBoard(result.board.map((c) => ({
          position: c.position,
          pieceId: c.piece_id,
          rotation: c.rotation,
          edges: byId.get(c.piece_id) ?? [0, 0, 0, 0],
        })));
        setStatus(`solved in ${result.events?.length ?? 0} events`);
      } else {
        setStatus(`outcome: ${result.outcome}${result.message ? ` — ${result.message}` : ""}`);
        setBoard([]);
      }
    } catch (e) {
      setStatus(`error: ${e}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Educational mode</h1>
      <p className="text-zinc-600">Generates a small puzzle in your browser and solves it locally with the naive DFS algorithm. No server, no network.</p>
      <div className="flex gap-3 items-end flex-wrap">
        <label className="flex flex-col text-sm">
          Size
          <input type="number" min={2} max={6} value={size} onChange={(e) => setSize(+e.target.value)} className="border rounded px-2 py-1 w-20" />
        </label>
        <label className="flex flex-col text-sm">
          Colors
          <input type="number" min={2} max={10} value={colors} onChange={(e) => setColors(+e.target.value)} className="border rounded px-2 py-1 w-20" />
        </label>
        <label className="flex flex-col text-sm">
          Seed
          <input type="number" value={seed} onChange={(e) => setSeed(+e.target.value)} className="border rounded px-2 py-1 w-28" />
        </label>
        <label className="flex flex-col text-sm">
          Traversal
          <select value={traversal} onChange={(e) => setTraversal(e.target.value as "row_by_row" | "spiral")} className="border rounded px-2 py-1">
            <option value="row_by_row">Row by row</option>
            <option value="spiral">Spiral</option>
          </select>
        </label>
        <button
          onClick={run}
          disabled={running}
          className="px-3 py-1 rounded bg-zinc-900 text-white disabled:opacity-60"
        >
          {running ? "Running..." : "Generate + solve"}
        </button>
        <span className="text-sm text-zinc-600">{status}</span>
      </div>
      <Board width={width} height={width} placements={board} />
    </section>
  );
}
