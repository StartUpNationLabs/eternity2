import {atom, RecoilState} from "recoil";
import {convertToPieces, createBoard, shuffleAndRotateBoard} from "../../utils/logic.tsx";
import {Board} from "../requestForm/atoms.ts";
import {
    BOARD_COLOR_MAX,
    BOARD_COLOR_MIN,
    BOARD_SIZE_MAX,
    BOARD_SIZE_MIN, CACHE_PULL_INTERVAL_DEFAULT, HASH_THRESHOLD_DEFAULT,
    SPIRAL_PATH_NAME, THREADS_DEFAULT, USE_CACHE_DEFAULT, WAIT_TIME_DEFAULT
} from "../../utils/Constants.tsx";


export const isSolvingStatisticsState: RecoilState<boolean> = atom({
    key: "isSolvingStatisticsState",
    default: false,
});

export const settingsStatisticsState
    = atom({
    key: 'settingsStatisticsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSizeMin: BOARD_SIZE_MIN,
        boardSizeMax: BOARD_SIZE_MAX,
        patternSizeMin: BOARD_COLOR_MIN,
        patternSizeMax: BOARD_COLOR_MAX,
        path: SPIRAL_PATH_NAME,
        useCache: USE_CACHE_DEFAULT,
        hashThreshold: HASH_THRESHOLD_DEFAULT,
        waitTime: WAIT_TIME_DEFAULT,
        cachePullInterval: CACHE_PULL_INTERVAL_DEFAULT,
        threads: THREADS_DEFAULT,
        timeout: 5000,
        sampleSize: 10,
    },
});

export const generatedBoardsState: RecoilState<Board[]> = atom({
    key: "generatedBoardsState",
    default: [],
});

export function generateBoards(minSize: number, maxSize: number, minColors: number, maxColors: number, sampleSize: number): Board[] {
    const boards = [] as Board[];
    for (let size = minSize; size <= maxSize; size++) {
        for (let colors = minColors; colors <= maxColors; colors++) {
            for (let i = 0; i < sampleSize; i++) {
                boards.push({
                    label: `${size}x${size} with ${colors} colors - Sample ${i + 1}`,
                    pieces: convertToPieces(shuffleAndRotateBoard(createBoard(size, colors))).map((piece, index) => ({
                        index: index,
                        piece: piece,
                        rotation: 0,
                    })),
                    nbColors: colors,
                });
            }
        }
    }
    return boards;
}
