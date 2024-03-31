import {Piece} from "../proto/solver/v1/solver.ts";

export interface PieceData {
    top: string;
    right: string;
    bottom: string;
    left: string;
}

export function generateInnerSymbols(size: number, numberOfSymbols: number) {
    const verticalSymbols = Array.from({length: size}, () =>
        Array.from({length: size - 1}, () => Math.floor(Math.random() * (numberOfSymbols - 1)) + 1)
    );
    const horizontalSymbols = Array.from({length: size - 1}, () =>
        Array.from({length: size}, () => Math.floor(Math.random() * (numberOfSymbols - 1)) + 1)
    );

    return {verticalSymbols, horizontalSymbols};
}

export function createBoard(size: number, numberOfSymbols: number) {
    numberOfSymbols += 1; // Add 1 to account for the border symbol
    const {verticalSymbols, horizontalSymbols} = generateInnerSymbols(size, numberOfSymbols);
    const board = Array.from({length: size}, () =>
        Array.from({length: size}, () => ({
            top: "0000000000000000",
            right: "0000000000000000",
            bottom: "0000000000000000",
            left: "0000000000000000",
        }))
    );

    for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
            if (i > 0) board[i][j].top = horizontalSymbols[i - 1][j].toString(2).padStart(16, '0');
            if (i < size - 1) board[i][j].bottom = horizontalSymbols[i][j].toString(2).padStart(16, '0');
            if (j > 0) board[i][j].left = verticalSymbols[i][j - 1].toString(2).padStart(16, '0');
            if (j < size - 1) board[i][j].right = verticalSymbols[i][j].toString(2).padStart(16, '0');
        }
    }
    return board;
}

export function shuffleAndRotateBoard(board: PieceData[][]): PieceData[][] {
    const rotatedBoard = board.map(row =>
        row.map(piece => {
            const rotations = Math.floor(Math.random() * 4); // 0 to 3 rotations
            for (let i = 0; i < rotations; i++) {
                piece = {
                    top: piece.left,
                    right: piece.top,
                    bottom: piece.right,
                    left: piece.bottom,
                };
            }
            return piece;
        })
    );

    // Shuffle the rows of the board
    for (let i = rotatedBoard.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [rotatedBoard[i], rotatedBoard[j]] = [rotatedBoard[j], rotatedBoard[i]];
    }

    return rotatedBoard;
}

export function rotatePiece(piece: PieceData, rotations: number) {
    for (let i = 0; i < rotations; i++) {
        const {top, right, bottom, left} = piece;
        piece = {
            top: left,
            right: top,
            bottom: right,
            left: bottom,
        };
    }
    return piece;
}

export function convertToPieces(board: PieceData[][]): Piece[] {
    return board.flat().map(piece => ({
        top: parseInt(piece.top, 2) === 0 ? 65535 : parseInt(piece.top, 2),
        right: parseInt(piece.right, 2) === 0 ? 65535 : parseInt(piece.right, 2),
        bottom: parseInt(piece.bottom, 2) === 0 ? 65535 : parseInt(piece.bottom, 2),
        left: parseInt(piece.left, 2) === 0 ? 65535 : parseInt(piece.left, 2),
    }));
}

export function convertToBoard(pieces: Piece[]): PieceData[][] {
    const size = Math.sqrt(pieces.length);
    const board = pieces.map(({top, right, bottom, left}) => ({
        top: top.toString(2).padStart(16, '0'),
        right: right.toString(2).padStart(16, '0'),
        bottom: bottom.toString(2).padStart(16, '0'),
        left: left.toString(2).padStart(16, '0'),
    }));

    return Array.from({length: size}, (_, i) => board.slice(i * size, (i + 1) * size));

}


