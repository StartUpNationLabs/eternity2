import {atom, RecoilState} from "recoil";
import {convertToPieces, createBoard, shuffleAndRotateBoard} from "../../utils/logic.tsx";
import {Board} from "../requestForm/atoms.ts";


export const isSolvingStatisticsState: RecoilState<boolean> = atom({
    key: "isSolvingStatisticsState",
    default: false,
});

export const settingsStatisticsState
    = atom({
    key: 'settingsStatisticsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSizeMin: 2,
        boardSizeMax: 16,
        patternSizeMin: 2,
        patternSizeMax: 22,
        path: "Spiral",
        useCache: false,
        hashThreshold: 4,
        waitTime: 1000,
        cachePullInterval: 10,
        threads: 4,
        timeout: 5000,
        sampleSize: 10,
    },
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
