import {atom, RecoilState} from "recoil";
import {RotatedPiece, SolverSolveRequest} from "../../proto/solver/v1/solver.ts";
import {convertBucasBoardToRotatedPieces} from "../../utils/utils.tsx";
import {ETERNITY_II_PIECES} from "../../utils/Constants.tsx";


export const BOARD_SIZE_MIN = 2;
export const BOARD_SIZE_MAX = 16;
export const BOARD_SIZE_DEFAULT = 8;

export const BOARD_COLOR_MIN = 2;
export const BOARD_COLOR_MAX = 22;
export const BOARD_COLOR_DEFAULT = 12;


export interface Path {
    label: string;
    path: number[];
}

export interface Board {
    label: string;
    pieces: RotatedPiece[];
    nbColors: number;
}


export const eternity2OfficialBoard: Board = {
    label: "Eternity II Official",
    pieces: convertBucasBoardToRotatedPieces(ETERNITY_II_PIECES),
    nbColors: 22,
}

export const spiralPath = {
    label: "Spiral",
    path: [] as number[]
}

export const settingsState
    = atom({
    key: 'settingsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSize: BOARD_SIZE_DEFAULT,
        boardColors: BOARD_COLOR_DEFAULT,
        path: spiralPath,
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


export const pathsState: RecoilState<Path[]> = atom({
    key: 'pathsState',
    default: [...defaultPaths, spiralPath],
});

export const boardState: RecoilState<SolverSolveRequest["pieces"]> = atom({
    key: 'boardState',
    default: [] as SolverSolveRequest["pieces"],
});

export const boardsState: RecoilState<Board[]> = atom({
    key: 'boardsState',
    default: [eternity2OfficialBoard], // Add more boards here as needed
});

export const solveModeState = atom({
    key: 'solveModeState',
    default: 'none' as "normal" | "stepByStep" | "none" | "multiServer",
});

