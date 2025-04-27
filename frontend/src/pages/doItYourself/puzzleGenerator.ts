import { Piece } from "../../proto/solver/v1/solver.ts";
import { createBoard, shuffleAndRotateBoard } from "../../utils/logic.tsx";
import { BOARD_COLOR_DEFAULT } from "../../utils/Constants.tsx";

/**
 * Converts a board with piece data to an array of Piece objects
 * @param board - The board in PieceData format
 * @returns Array of Piece objects
 */
export function convertToPieces(board: any[][]): Piece[] {
    return board.flat().map(piece => ({
        top: parseInt(piece.top, 2) === 0 ? 65535 : parseInt(piece.top, 2),
        right: parseInt(piece.right, 2) === 0 ? 65535 : parseInt(piece.right, 2),
        bottom: parseInt(piece.bottom, 2) === 0 ? 65535 : parseInt(piece.bottom, 2),
        left: parseInt(piece.left, 2) === 0 ? 65535 : parseInt(piece.left, 2),
    }));
}

/**
 * Generates pieces for a puzzle of specified size
 * @param count - Total number of pieces (gridSize * gridSize)
 * @returns Array of Piece objects
 */
export function generateRandomPieces(count: number): Piece[] {
    const size = Math.sqrt(count);
    
    // Use the existing board creation and shuffling functions
    const board = createBoard(size, BOARD_COLOR_DEFAULT);
    const shuffledBoard = shuffleAndRotateBoard(board);
    const pieces = convertToPieces(shuffledBoard);
    
    return pieces;
} 