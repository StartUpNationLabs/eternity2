// The educational route loads the WASM bundle by a runtime URL because
// the bundle lives outside src/. Vite's `?url` import would be cleaner;
// for now we type the dynamic import.
declare module "@wasm/eternity2_wasm.js" {
  const initWasm: (input?: { module_or_path?: string }) => Promise<void>;
  export default initWasm;
  export function generatePuzzle(input: {
    size: number;
    interior_colors: number;
    seed: number | bigint;
  }): {
    width: number;
    height: number;
    color_count: number;
    pieces: Array<{ id: number; edges: [number, number, number, number] }>;
    fingerprint: bigint;
  };
  export function solveNaive(input: {
    puzzle: {
      width: number;
      height: number;
      color_count: number;
      pieces: Array<{ id: number; edges: [number, number, number, number] }>;
    };
    traversal: "row_by_row" | "spiral";
    time_budget_ms: number | bigint;
    all_solutions: boolean;
  }): {
    outcome: "solved" | "exhausted" | "timed_out" | "error";
    board?: Array<{ position: number; piece_id: number; rotation: number }>;
    message?: string;
    events?: Array<{ node_id: bigint; depth: number; timestamp_us: bigint; kind: string }>;
  };
}
