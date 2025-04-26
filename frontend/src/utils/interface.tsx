import {Hint, RotatedPiece} from "../proto/solver/v1/solver.ts";

export interface Path {
    label: string;
    path: number[];
}

export interface Board {
    label: string;
    pieces: RotatedPiece[];
    nbColors: number;
    hints: Hint[];
}
