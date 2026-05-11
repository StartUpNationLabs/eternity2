// Research mode — server-side portfolio solve.
// Connects to the tonic server via gRPC-Web (proxied through /grpc in
// dev; CORS-permissive on the server). The portfolio runner UI, sweep
// mode, and heuristic inspector listed in V2_DESIGN.md §"Research"
// build on top of this baseline solve+stream surface.

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { create } from "@bufbuild/protobuf";
import { Board, type PiecePlacement } from "../lib/Board";
import { solverClient } from "../lib/grpcClient";
import {
  ListSolversRequestSchema,
  SolveMode,
  SolveRequestSchema,
  type SolverEntry,
} from "../gen/solver/v2/solver_pb";

interface RunStats {
  events: number;
  nodes: bigint;
  status: string;
  board: PiecePlacement[];
}

export function ResearchRoute() {
  const listSolvers = useQuery({
    queryKey: ["list-solvers"],
    queryFn: async () => {
      const res = await solverClient.listSolvers(create(ListSolversRequestSchema));
      return res.entries;
    },
  });

  const [selected, setSelected] = useState<{ id: string; profile: string }>({
    id: "dlx",
    profile: "border_first_lcv",
  });
  const [size, setSize] = useState(4);
  const [colors, setColors] = useState(4);
  const [seed, setSeed] = useState(7);
  const [stats, setStats] = useState<RunStats | null>(null);
  const [running, setRunning] = useState(false);

  async function run() {
    setRunning(true);
    setStats({ events: 0, nodes: 0n, status: "generating puzzle in wasm...", board: [] });
    try {
      // Use the same WASM generator as educational mode for
      // determinism. Native generation on the server would be a fine
      // alternative; using WASM keeps the puzzle reproducible client-side.
      const init = (await import(/* @vite-ignore */ "@wasm/eternity2_wasm.js")) as unknown as {
        default: (i: { module_or_path: string }) => Promise<void>;
        generatePuzzle: (i: { size: number; interior_colors: number; seed: number }) => {
          width: number; height: number; color_count: number;
          pieces: Array<{ id: number; edges: [number, number, number, number] }>;
        };
      };
      await init.default({ module_or_path: "/wasm/pkg/eternity2_wasm_bg.wasm" });
      const puzzle = init.generatePuzzle({ size, interior_colors: colors, seed });
      const byId = new Map(puzzle.pieces.map((p) => [p.id, p.edges]));

      const req = create(SolveRequestSchema, {
        puzzle: {
          width: puzzle.width,
          height: puzzle.height,
          colorCount: puzzle.color_count,
          pieces: puzzle.pieces.map((p) => ({ id: p.id, edges: p.edges.map((e) => e) })),
          puzzleHash: "",
        },
        selections: [{
          solverId: selected.id,
          heuristicProfile: selected.profile,
          seed: 0n,
        }],
        mode: SolveMode.FIRST_SOLUTION,
        timeBudgetMs: 30_000n,
        maxSolutions: 0,
      });

      let events = 0;
      let nodes = 0n;
      let board: PiecePlacement[] = [];
      let status = "solving...";
      setStats({ events, nodes, status, board });

      for await (const ev of solverClient.solve(req)) {
        events += 1;
        if (ev.body.case === "stats") {
          nodes = ev.body.value.nodes;
        }
        if (ev.body.case === "solved" && ev.body.value.board) {
          board = ev.body.value.board.cells.map((c) => ({
            position: c.position,
            pieceId: c.pieceId,
            rotation: c.rotation,
            edges: byId.get(c.pieceId) ?? [0, 0, 0, 0],
          }));
          status = "solved";
        } else if (ev.body.case === "exhausted") {
          status = "exhausted";
        } else if (ev.body.case === "timedOut") {
          status = "timed out";
        } else if (ev.body.case === "cancelled") {
          status = "cancelled";
        }
        if (events % 8 === 0 || status !== "solving...") {
          setStats({ events, nodes, status, board });
        }
      }
    } catch (e) {
      setStats((s) => ({ ...(s ?? { events: 0, nodes: 0n, board: [] }), status: `error: ${e}` }));
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Research mode</h1>
      <p className="text-zinc-600">Runs a solver on the server and streams the search trace back over gRPC-Web.</p>

      {listSolvers.isLoading && <p>Loading solver portfolio…</p>}
      {listSolvers.error && <p className="text-red-600">Failed to reach server: {String(listSolvers.error)}</p>}

      {listSolvers.data && (
        <div className="space-y-2">
          <div className="flex gap-2 flex-wrap">
            {listSolvers.data.map((s: SolverEntry) =>
              s.heuristicProfiles.map((p) => {
                const sel = selected.id === s.solverId && selected.profile === p.id;
                return (
                  <button
                    key={`${s.solverId}/${p.id}`}
                    onClick={() => setSelected({ id: s.solverId, profile: p.id })}
                    className={`px-3 py-1 rounded border text-sm ${sel ? "bg-zinc-900 text-white" : "bg-white"}`}
                  >
                    {s.displayName} · {p.displayName}
                  </button>
                );
              }),
            )}
          </div>
          <div className="flex gap-3 items-end flex-wrap">
            <label className="flex flex-col text-sm">Size
              <input type="number" min={2} max={9} value={size} onChange={(e) => setSize(+e.target.value)} className="border rounded px-2 py-1 w-20" />
            </label>
            <label className="flex flex-col text-sm">Colors
              <input type="number" min={2} max={10} value={colors} onChange={(e) => setColors(+e.target.value)} className="border rounded px-2 py-1 w-20" />
            </label>
            <label className="flex flex-col text-sm">Seed
              <input type="number" value={seed} onChange={(e) => setSeed(+e.target.value)} className="border rounded px-2 py-1 w-28" />
            </label>
            <button onClick={run} disabled={running} className="px-3 py-1 rounded bg-zinc-900 text-white disabled:opacity-60">
              {running ? "Running…" : "Run on server"}
            </button>
          </div>
        </div>
      )}

      {stats && (
        <div className="space-y-2">
          <div className="text-sm text-zinc-600">
            events: {stats.events} · nodes: {String(stats.nodes)} · status: {stats.status}
          </div>
          <Board width={size} height={size} placements={stats.board} />
        </div>
      )}
    </section>
  );
}
