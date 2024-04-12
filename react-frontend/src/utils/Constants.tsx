import {Path} from "./interface.tsx";

/**
 * Values used for the settings
 */
export const BOARD_SIZE_MIN = 2;
export const BOARD_SIZE_MAX = 16;
export const BOARD_SIZE_DEFAULT = 8;
export const BOARD_SIZE_STEP = 1;

export const BOARD_COLOR_MIN = 2;
export const BOARD_COLOR_MAX = 22;
export const BOARD_COLOR_DEFAULT = 12;
export const BOARD_COLOR_STEP = 1;

export const HASH_THRESHOLD_MIN = 1;
export const HASH_THRESHOLD_MAX = 100;
export const HASH_THRESHOLD_DEFAULT = 4;
export const HASH_THRESHOLD_STEP = 1;

export const WAIT_TIME_MIN = 50;
export const WAIT_TIME_MAX = 2050;
export const WAIT_TIME_DEFAULT = 500;
export const WAIT_TIME_STEP = 100;

export const CACHE_PULL_INTERVAL_MIN = 1;
export const CACHE_PULL_INTERVAL_MAX = 60;
export const CACHE_PULL_INTERVAL_DEFAULT = 10;
export const CACHE_PULL_INTERVAL_STEP = 1;

export const THREADS_MIN = 1;
export const THREADS_MAX = 64;
export const THREADS_DEFAULT = 32;
export const THREADS_STEP = 1;

export const USE_CACHE_DEFAULT = false;

/**
 * Path names
 */
export const SCAN_ROW_PATH_NAME = "Scan Row";
export const SPIRAL_PATH_NAME = "Spiral";

export const MULTI_SERVER_BASE_URLS = [
    {
        "name": "node-apoorva-3",
        "url": "http://node-apoorva3-abklev50.k3s.hs.ozeliurs.com:50052",
    },
    {
        "name": "node-apoorva-2",
        "url": "http://node-apoorva2.k3s.hs.ozeliurs.com:50052",
    },
    {
        "name": "vmpx15",
        "url": "http://vmpx15.polytech.hs.ozeliurs.com:50052",
    },
    {
        "name": "vmpx12",
        "url": "http://vmpx12.polytech.hs.ozeliurs.com:50052",
    },
    {
        "name": "vmpx13",
        "url": "http://vmpx13.polytech.hs.ozeliurs.com:50052",
    },
    {
        "name": "abel",
        "url": "http://vmpx15.polytech.hs.ozeliurs.com:50056",
    },
]
export const SERVER_BASE_URL: string = "http://node-apoorva3-abklev50.k3s.hs.ozeliurs.com:50052"

/**
 * Directions for the pieces
 */
export enum Direction {
    Top,
    Right,
    Bottom,
    Left,
}

export enum Rotation {
    ZERO,
    NINETY,
    ONE_EIGHTY,
    TWO_SEVENTY,
}

export const abortController = {
    abortController: new AbortController(),
}

export const DEFAULT_SPIRAL_PATH = {
    label: SPIRAL_PATH_NAME,
    // It is empty because the server is doing spiral by default
    // An empty path will be considered as an error by the server and will be replaced by the default spiral path
    path: [] as number[],
    hints: []
}

export const DEFAULT_PATHS: Path[] = [...Array(16).keys()].map(
    i => ({
        label: SCAN_ROW_PATH_NAME,
        path: [...[...Array((i + 2) * (i + 2) - 1).keys()].map(j => j + 1), 2147483647],
        hints: []
    })
);

// Create a default path for the board size : BOARD_SIZE_DEFAULT
export const DEFAULT_SCAN_ROW_PATH = {
    label: SCAN_ROW_PATH_NAME,
    path: [...[...Array(BOARD_SIZE_DEFAULT * BOARD_SIZE_DEFAULT - 1).keys()].map(j => j + 1),
        2147483647
    ],
    hints: [],
};

export enum SolveMode {
    none,
    normal,
    stepByStep,
    multiServer,
}
