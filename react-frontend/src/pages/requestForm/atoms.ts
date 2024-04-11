import {atom, RecoilState} from "recoil";
import {SolverSolveRequest} from "../../proto/solver/v1/solver.ts";
import {
    BOARD_COLOR_DEFAULT,
    BOARD_SIZE_DEFAULT,
    CACHE_PULL_INTERVAL_DEFAULT,
    DEFAULT_PATHS,
    DEFAULT_SCAN_ROW_PATH,
    DEFAULT_SPIRAL_PATH,
    HASH_THRESHOLD_DEFAULT,
    SolveMode,
    THREADS_DEFAULT,
    USE_CACHE_DEFAULT,
    WAIT_TIME_DEFAULT
} from "../../utils/Constants.tsx";
import {Board, Path} from "../../utils/interface.tsx";
import {
    ETERNITY_II_OFFICIAL_BOARD_ALL_HINTS,
    ETERNITY_II_OFFICIAL_BOARD_CENTER_HINT,
    ETERNITY_II_OFFICIAL_BOARD_NO_HINTS
} from "../../utils/OfficialEternity2.tsx";


export const pathsState: RecoilState<Path[]> = atom({
    key: 'pathsState',
    default: [...DEFAULT_PATHS, DEFAULT_SPIRAL_PATH],
});

export const settingsState
    = atom({
    key: 'settingsState',
    default: {
        boardSize: BOARD_SIZE_DEFAULT as number,
        boardColors: BOARD_COLOR_DEFAULT,
        path: DEFAULT_SCAN_ROW_PATH as Path,
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

export const hintsState: RecoilState<SolverSolveRequest["hints"]> = atom({
    key: 'hintsState',
    default: [] as SolverSolveRequest["hints"],
});

export interface HintTemplate {
    label: string;
    pieceIndex: number[];
    boardSize: number;
}

export const hintTemplatesState: RecoilState<HintTemplate[]> = atom({
    key: 'hintTemplatesState',
    default: [] as HintTemplate[],
});

export const boardsState: RecoilState<Board[]> = atom({
    key: 'boardsState',
    default: [ETERNITY_II_OFFICIAL_BOARD_ALL_HINTS, ETERNITY_II_OFFICIAL_BOARD_CENTER_HINT, ETERNITY_II_OFFICIAL_BOARD_NO_HINTS],
});

export const solveModeState = atom({
    key: 'solveModeState',
    default: SolveMode.none,
});

