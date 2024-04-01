import {atom, RecoilState} from "recoil";
import {RotatedPiece, SolverSolveRequest} from "../../proto/solver/v1/solver.ts";
import {convertBucasBoardToRotatedPieces} from "../../utils/utils.tsx";
import {
    BOARD_COLOR_DEFAULT,
    BOARD_SIZE_DEFAULT,
    CACHE_PULL_INTERVAL_DEFAULT,
    ETERNITY_II_PIECES,
    HASH_THRESHOLD_DEFAULT,
    SCAN_ROW_PATH_NAME,
    SPIRAL_PATH_NAME,
    THREADS_DEFAULT,
    USE_CACHE_DEFAULT,
    WAIT_TIME_DEFAULT
} from "../../utils/Constants.tsx";


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
    label: SPIRAL_PATH_NAME,
    // It is empty because the server is doing spiral by default
    // An empty path will be considered as an error by the server and will be replaced by the default spiral path
    path: [] as number[]
}


export const defaultPaths: Path[] = [...Array(16).keys()].map(
    i => ({
        label: SCAN_ROW_PATH_NAME,
        path: [...[...Array((i + 2) * (i + 2) - 1).keys()].map(j => j + 1), 2147483647]
        ,
    })
);

// Create a default path for the board size : BOARD_SIZE_DEFAULT
const DEFAULT_SCAN_ROW_PATH = {
    label: SCAN_ROW_PATH_NAME,
    path: [...[...Array(BOARD_SIZE_DEFAULT * BOARD_SIZE_DEFAULT - 1).keys()].map(j => j + 1),
        2147483647
    ]
};

export const pathsState: RecoilState<Path[]> = atom({
    key: 'pathsState',
    default: [...defaultPaths, spiralPath],
});


export const settingsState
    = atom({
    key: 'settingsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSize: BOARD_SIZE_DEFAULT,
        boardColors: BOARD_COLOR_DEFAULT,
        // Take the scan row path by default that corresponds to the board size
        // Filter by name and then by length to avoid conflicts with the spiral path
        path: DEFAULT_SCAN_ROW_PATH,
        useCache: USE_CACHE_DEFAULT,
        hashThreshold: HASH_THRESHOLD_DEFAULT,
        waitTime: WAIT_TIME_DEFAULT,
        cachePullInterval: CACHE_PULL_INTERVAL_DEFAULT,
        threads: THREADS_DEFAULT,
    }, // default value (aka initial value)
});


export const boardState: RecoilState<SolverSolveRequest["pieces"]> = atom({
    key: 'boardState',
    default: [] as SolverSolveRequest["pieces"],
});

export const boardsState: RecoilState<Board[]> = atom({
    key: 'boardsState',
    default: [eternity2OfficialBoard],
});

export const solveModeState = atom({
    key: 'solveModeState',
    default: 'none' as "normal" | "stepByStep" | "none" | "multiServer",
});

