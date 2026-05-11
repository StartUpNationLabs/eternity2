import { create, toBinary, fromBinary } from "@bufbuild/protobuf";
import {
  SolverEventSchema,
  PathConfigSchema,
  SolveRequestSchema,
  SolveMode,
  NaiveTraversal,
  SupportedPathPolicy,
  type SolverEvent,
  type PathConfig,
  type SolveRequest,
} from "../gen/solver/v2/solver_pb.js";

const event: SolverEvent = create(SolverEventSchema, {
  schemaVersion: 1,
  solverRunId: 42n,
  nodeId: 7n,
  depth: 3,
  timestampUs: 123_456n,
  body: {
    case: "started",
    value: {
      solverId: "dlx",
      heuristicProfile: "border_first_lcv",
      puzzleHash: "deadbeef",
      seed: 1n,
      startedWallUs: 0n,
    },
  },
});

const bytes = toBinary(SolverEventSchema, event);
const decoded = fromBinary(SolverEventSchema, bytes);
if (decoded.schemaVersion !== 1) throw new Error("schema_version mismatch");
if (decoded.body.case !== "started") throw new Error("oneof mismatch");

const path: PathConfig = create(PathConfigSchema, {
  path: [0, 1, 2, 3],
  policy: {
    case: "prefixConstraint",
    value: { k: 4 },
  },
});

const request: SolveRequest = create(SolveRequestSchema, {
  mode: SolveMode.FIRST_SOLUTION,
  timeBudgetMs: 5_000n,
  selections: [
    {
      solverId: "naive",
      heuristicProfile: "row_by_row",
      seed: 0n,
      options: {
        case: "naive",
        value: { allowRotation: true, traversal: NaiveTraversal.ROW_BY_ROW },
      },
    },
  ],
  pathConfig: path,
});

void request;
void SupportedPathPolicy.STRICT;
