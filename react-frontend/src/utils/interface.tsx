import {RotatedPiece} from "../proto/solver/v1/solver.ts";

export interface Path {
    label: string;
    path: number[];
    hints: Hint[];
}

export interface Hint {
    index: number;
    x: number;
    y: number;
    rotation: number;
}

export interface Board {
    label: string;
    pieces: RotatedPiece[];
    nbColors: number;
    hints: Hint[];
}
