import {atom, RecoilState} from "recoil";
import {RotatedPiece, SolverSolveRequest} from "../../proto/solver/v1/solver.ts";
import {convertBucasBoardToRotatedPieces} from "../../utils/utils.tsx";
import {ETERNITY_II_PIECES} from "../../utils/Constants.tsx";

export interface Path {
    label: string;
    path: number[];
}

export interface Board {
    label: string;
    gridSideSize: number;
    pieces: RotatedPiece[];
}

export const settingsState
    = atom({
    key: 'settingsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSize: 4,
        boardColors: 4,
        path: {
            label: `Default`,
            path: [] as number[]
        },
        useCache: false,
        hashThreshold: 4,
        waitTime: 1000,
        cachePullInterval: 10,
        threads: 4,
    }, // default value (aka initial value)
});


const defaultPaths: Path[] = [...Array(16).keys()].map(
    i => ({
        label: `Scan Row`,
        path: [...[...Array((i + 2) * (i + 2) - 1).keys()].map(j => j + 1), 2147483647]
        ,
    })
);
export const defaultPath = {
    label: "Default",
    path: []
}


export const pathsState: RecoilState<Path[]> = atom({
    key: 'pathsState',
    default: [...defaultPaths, defaultPath],
});

export const boardState: RecoilState<SolverSolveRequest["pieces"]> = atom({
    key: 'boardState',
    default: [] as SolverSolveRequest["pieces"],
});


export const solveModeState = atom({
    key: 'solveModeState',
    default: 'none' as "normal" | "stepByStep" | "none",
});

export const eternity2OfficialBoard: Board = {
    label: "Eternity II Official",
    gridSideSize: 16,
    pieces: convertBucasBoardToRotatedPieces(ETERNITY_II_PIECES),
}
