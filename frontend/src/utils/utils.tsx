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

/**
 * Parses a CSV file containing solved puzzle data
 * Supports multiple CSV formats:
 * 1. Standard format: boardSize\n top,right,bottom,left,isHint,x,y[,rotation,...]
 * 2. Solution format: top,right,bottom,left,pos_x,rotation (no board size line)
 * 
 * @param csvContent The CSV file content as a string
 * @returns Object containing pieces array, board size, and hints array
 */
export function parsePuzzleCSV(csvContent: string): {
    pieces: Piece[];
    boardSize: number;
    hints: Hint[];
} {
    const lines = csvContent.trim().split(/\r?\n/).filter(line => line.trim());
    
    if (lines.length === 0) {
        throw new Error('CSV file is empty');
    }

    let boardSize: number;
    let startLine = 0;
    
    // Try to parse first line as board size
    const firstLineValue = parseInt(lines[0].trim(), 10);
    if (!isNaN(firstLineValue) && firstLineValue > 0 && firstLineValue <= 20) {
        // First line is board size
        boardSize = firstLineValue;
        startLine = 1;
    } else {
        // No board size line, calculate from number of pieces
        // We'll calculate it after parsing all pieces
        boardSize = 0;
        startLine = 0;
    }

    const pieces: Piece[] = [];
    const hints: Hint[] = [];

    // Parse each piece line
    for (let i = startLine; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        
        // Skip header rows (lines that don't start with a binary string)
        if (i === startLine && !line.match(/^[01,]+/)) {
            // This might be a header row, skip it
            continue;
        }

        // Parse CSV line, handling quoted fields
        const parts: string[] = [];
        let current = '';
        let inQuotes = false;
        
        for (let j = 0; j < line.length; j++) {
            const char = line[j];
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                parts.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        parts.push(current.trim()); // Add the last field
        
        // If simple split works better, try that as fallback
        if (parts.length < 6) {
            // Try simple comma split as fallback
            const simpleParts = line.split(',').map(p => p.trim().replace(/^"|"$/g, ''));
            if (simpleParts.length >= 6) {
                parts.splice(0, parts.length, ...simpleParts);
            }
        }
        
        // Handle different CSV formats
        // Format 1: top,right,bottom,left,isHint,x,y[,rotation,...] (7+ fields)
        // Format 2: top,right,bottom,left,pos_x,rotation (6 fields) - solution format
        if (parts.length < 6) {
            throw new Error(
                `Invalid CSV line ${i + 1}: insufficient fields (got ${parts.length}, expected at least 6). ` +
                `Line content: ${line.substring(0, 100)}`
            );
        }

        // Parse binary strings to numbers
        // Based on C++ code: a=top, b=right, c=bottom, d=left
        // make_piece(top, right, down, left) confirms this order
        const topStr = parts[0];
        const rightStr = parts[1];
        const bottomStr = parts[2];
        const leftStr = parts[3];
        
        let isHint = false;
        let x = 0;
        let y = 0;
        let rotation = 0;
        
        if (parts.length >= 7) {
            // Standard format: top,right,bottom,left,isHint,x,y[,rotation,...]
            isHint = parseInt(parts[4], 10) === 1;
            x = parseInt(parts[5], 10);
            y = parseInt(parts[6], 10);
            rotation = parts.length > 7 ? parseInt(parts[7], 10) || 0 : 0;
        } else if (parts.length === 6) {
            // Solution format: top,right,bottom,left,pos_x,rotation
            // pos_x is the position index (0-based), we'll convert to x,y after we know board size
            // For now, we'll set isHint to false and x,y to 0
            rotation = parseInt(parts[5], 10) || 0;
            isHint = false;
            // x,y will be calculated after we know board size if needed
        }

        // Convert binary strings to numbers
        // Empty string, "0", or "0000000000000000" means border/empty, use 65535
        // "1111111111111111" (all 1s) also represents border = 65535
        const parseEdge = (edgeStr: string): number => {
            if (!edgeStr || edgeStr === '0' || edgeStr === '') return 65535;
            const parsed = parseInt(edgeStr, 2);
            if (isNaN(parsed)) return 65535;
            // 0 or 65535 (all 1s in 16 bits) means border
            return parsed === 0 ? 65535 : parsed;
        };

        const top = parseEdge(topStr);
        const right = parseEdge(rightStr);
        const bottom = parseEdge(bottomStr);
        const left = parseEdge(leftStr);

        const piece: Piece = {
            top,
            right,
            bottom,
            left,
        };

        pieces.push(piece);

        // If this is a hint, add it to hints array
        if (isHint && !isNaN(x) && !isNaN(y)) {
            const index = pieces.length - 1; // Index in the pieces array
            hints.push({
                index,
                x,
                y,
                rotation,
            });
        }
    }

    // Calculate board size if not provided
    if (boardSize === 0) {
        boardSize = Math.sqrt(pieces.length);
        if (!Number.isInteger(boardSize) || boardSize <= 0) {
            throw new Error(`Cannot determine board size from ${pieces.length} pieces (not a perfect square)`);
        }
    }

    // Validate that we have the correct number of pieces
    const expectedPieces = boardSize * boardSize;
    if (pieces.length !== expectedPieces) {
        throw new Error(`Expected ${expectedPieces} pieces but found ${pieces.length}`);
    }

    return { pieces, boardSize, hints };
}

/**
 * Exports the current puzzle board to CSV format
 * CSV format:
 * - First line: board size (integer)
 * - Subsequent lines: top,right,bottom,left,isHint,x,y,rotation,0,0
 *   where top/right/bottom/left are binary strings
 * 
 * @param pieces Array of Piece objects
 * @param boardSize Size of the board (e.g., 4 for 4x4)
 * @param hints Array of Hint objects (optional)
 * @returns CSV string representation of the puzzle
 */
export function exportPuzzleToCSV(
    pieces: Piece[],
    boardSize: number,
    hints: Hint[] = []
): string {
    const lines: string[] = [];
    
    // First line: board size
    lines.push(boardSize.toString());
    
    // Create a map of hint indices for quick lookup
    const hintMap = new Map<number, Hint>();
    hints.forEach(hint => {
        // Use the hint's index directly
        hintMap.set(hint.index, hint);
    });
    
    // Export each piece
    for (let i = 0; i < pieces.length; i++) {
        const piece = pieces[i];
        const x = i % boardSize;
        const y = Math.floor(i / boardSize);
        
        // Check if this piece index is a hint
        const hint = hintMap.get(i);
        const isHint = hint !== undefined ? 1 : 0;
        // Use hint's x,y if available, otherwise calculate from index
        const hintX = hint?.x !== undefined ? hint.x : x;
        const hintY = hint?.y !== undefined ? hint.y : y;
        const rotation = hint?.rotation || 0;
        
        // Convert numeric values to binary strings (16 bits)
        // 65535 (border) should be represented as "1111111111111111" or "0000000000000000"
        const toBinary = (value: number): string => {
            if (value === 65535) {
                return "1111111111111111"; // Border value
            }
            return value.toString(2).padStart(16, '0');
        };
        
        const top = toBinary(piece.top);
        const right = toBinary(piece.right);
        const bottom = toBinary(piece.bottom);
        const left = toBinary(piece.left);
        
        // Format: top,right,bottom,left,isHint,x,y,rotation,0,0
        // Use hint x,y if this is a hint, otherwise use calculated x,y
        const exportX = isHint ? hintX : x;
        const exportY = isHint ? hintY : y;
        lines.push(`${top},${right},${bottom},${left},${isHint},${exportX},${exportY},${rotation},0,0`);
    }
    
    return lines.join('\n');
}

