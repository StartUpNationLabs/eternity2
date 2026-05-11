// Smoke test the WASM bundle from Node. The `web` target uses ESM, so
// Node 22+ can import it directly with a small init shim.
import { readFile } from "node:fs/promises";
import init, { generatePuzzle, solveNaive } from "./pkg/eternity2_wasm.js";

const wasm = await readFile(new URL("./pkg/eternity2_wasm_bg.wasm", import.meta.url));
await init({ module_or_path: wasm });

const puzzle = generatePuzzle({ size: 4, interior_colors: 4, seed: 7 });
console.log("puzzle:", puzzle.width, "x", puzzle.height, "pieces:", puzzle.pieces.length, "fp:", puzzle.fingerprint);

const result = solveNaive({
  puzzle: {
    width: puzzle.width,
    height: puzzle.height,
    color_count: puzzle.color_count,
    pieces: puzzle.pieces,
  },
  traversal: "row_by_row",
  time_budget_ms: 5000,
  all_solutions: false,
});
console.log("outcome:", result.outcome, "events:", result.events?.length ?? 0);
if (result.outcome !== "solved") {
  process.exit(1);
}
console.log("first 5 placements:", result.board.slice(0, 5));
