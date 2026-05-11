import { createClient } from "@connectrpc/connect";
import { createGrpcWebTransport } from "@connectrpc/connect-web";
import { SolverService } from "../gen/solver/v2/solver_pb";

const baseUrl = import.meta.env.DEV ? "/grpc" : (import.meta.env.VITE_GRPC_BASE_URL ?? "");

export const transport = createGrpcWebTransport({ baseUrl });
export const solverClient = createClient(SolverService, transport);
