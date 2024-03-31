import {atom, RecoilState} from "recoil";
import {SolverSolveResponse} from "../../proto/solver/v1/solver.ts";

export const solverSolveResponseState: RecoilState<SolverSolveResponse[]> = atom({
    key: "solverSolveResponseState",
    default: [] as SolverSolveResponse[],
});

export const isSolvingState: RecoilState<boolean> = atom({
    key: "isSolvingState",
    default: false,
});


export const isSolvingStepByStepState: RecoilState<boolean> = atom({
    key: "isSolvingStepByStepState",
    default: false,
});

export const isSolvingMultiServerState: RecoilState<boolean> = atom({
    key: "isSolvingMultiServerState",
    default: false,
});