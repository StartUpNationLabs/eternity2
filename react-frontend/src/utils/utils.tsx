import React from "react";
import {Piece, RotatedPiece} from "../proto/solver/v1/solver.ts";

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
