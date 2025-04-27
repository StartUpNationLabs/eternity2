import React from "react";
import {Hint, Piece, RotatedPiece} from "../proto/solver/v1/solver.ts";

export function useStateHistory<T>(
    initialValue?: T | (() => T)
): [T | undefined, (state: T) => void, Array<T>] {
    const [allStates, setState] = React.useReducer(
        (oldState: T[], newState: T) => {
            return [...oldState, newState];
        },
        typeof initialValue === "function"
            ? [(initialValue as () => T)()]
            : initialValue !== undefined
                ? [initialValue as T]
                : []
    );

    const currentState = allStates[allStates.length - 1];
    const stateHistory = allStates.slice(0, allStates.length - 1);
    return [currentState, setState, stateHistory];
}

export function convertBucasToPiece(bucas: string): Piece {
    // Convert the bucas string to a Piece object
    return {
        top: bucas.charCodeAt(0) - 'a'.charCodeAt(0) || 65535,
        right: bucas.charCodeAt(1) - 'a'.charCodeAt(0) || 65535,
        bottom: bucas.charCodeAt(2) - 'a'.charCodeAt(0) || 65535,
        left: bucas.charCodeAt(3) - 'a'.charCodeAt(0) || 65535,
    };
}

export function convertBucasBoardToRotatedPieces(bucasBoard: string[]): RotatedPiece[] {
    return bucasBoard.map((bucas, index) => {
        return {
            piece: convertBucasToPiece(bucas),
            rotation: 0,
            index: index,
        };
    });
}

export function numberOfColorsThatFitInABoard(boardSize: number): number {
    return 2 * (boardSize ** 2 - boardSize);
}

export function boardRearrangedWithHints(rotatedPieces: RotatedPiece[], hints: Hint[]): RotatedPiece[] {
    /**
     /*
     export interface Hint {
    x: number;
    /**
     * @generated from protobuf field: int32 y = 3;
     y: number;
     /**
     * @generated from protobuf field: int32 rotation = 4;
     rotation: number;
     }
     export interface RotatedPiece {
    /**
     * @generated from protobuf field: solver.v1.Piece piece = 1;
     piece?: Piece;
     /**
     * @generated from protobuf field: uint32 rotation = 2;
     rotation: number;
     /**
     * @generated from protobuf field: uint32 index = 3;
     index: number;
     }
     */

    for (const hint of hints) {
        // Hint piece
        const piece = rotatedPieces.find(piece => piece.index === hint.index);
        if (piece) {
            piece.rotation = hint.rotation;
        }

        // Convert 2D x,y position to 1D index
        const position = hint.y * Math.sqrt(rotatedPieces.length) + hint.x;

        // Piece that is at the hint position
        const pieceAtPosition = rotatedPieces.find(piece => piece.index === position);

        // Swap the pieces
        if (piece && pieceAtPosition) {
            const temp = piece.piece;
            piece.piece = pieceAtPosition.piece;
            pieceAtPosition.piece = temp;
        }
    }

    return rotatedPieces;
}

