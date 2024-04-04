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
export const HASH_THRESHOLD_MAX = 32;
export const HASH_THRESHOLD_DEFAULT = 4;
export const HASH_THRESHOLD_STEP = 1;

export const WAIT_TIME_MIN = 50;
export const WAIT_TIME_MAX = 2050;
export const WAIT_TIME_DEFAULT = 500;
export const WAIT_TIME_STEP = 100;

export const CACHE_PULL_INTERVAL_MIN = 1;
export const CACHE_PULL_INTERVAL_MAX = 20;
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

export const MULTI_SERVER_BASE_URLS = [{
    "name": "server1",
    "url": "http://node-apoorva3-abklev50.k3s.hs.ozeliurs.com:50052",
}, {
    "name": "server2",
    "url": "http://node-apoorva2.k3s.hs.ozeliurs.com:50052",
}
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
