#!/usr/bin/env node

/**
 * Standalone Puzzle Generator Script
 *
 * Generates Eternity II-style puzzles with specified parameters
 *
 * Usage:
 *   node generate_puzzles.js --size 4 --colors 8 --count 3 --output ./data/puzzles
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Board generation functions (ported from frontend logic)

function numberOfColorsThatFitInABoard(boardSize) {
    return 2 * (boardSize ** 2 - boardSize);
}

function generateInnerSymbols(size, numberOfSymbols) {
    // Calculate how many edges we need to fill
    const numVerticalEdges = size * (size - 1);
    const numHorizontalEdges = (size - 1) * size;
    const totalEdges = numVerticalEdges + numHorizontalEdges;

    // Create an array with all symbols (1 to numberOfSymbols-1, excluding border 0)
    const availableSymbols = Array.from({length: numberOfSymbols - 1}, (_, i) => i + 1);

    // Generate edge symbols ensuring all colors are used
    const allEdges = [];

    // First, place each symbol at least once
    for (let i = 0; i < availableSymbols.length; i++) {
        if (allEdges.length < totalEdges) {
            allEdges.push(availableSymbols[i]);
        }
    }

    // Fill remaining edges with random symbols from the available set
    while (allEdges.length < totalEdges) {
        const randomSymbol = availableSymbols[Math.floor(Math.random() * availableSymbols.length)];
        allEdges.push(randomSymbol);
    }

    // Shuffle the edges to distribute colors randomly
    for (let i = allEdges.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [allEdges[i], allEdges[j]] = [allEdges[j], allEdges[i]];
    }

    // Split into vertical and horizontal edges
    const verticalEdges = allEdges.slice(0, numVerticalEdges);
    const horizontalEdges = allEdges.slice(numVerticalEdges);

    // Convert to 2D arrays
    const verticalSymbols = [];
    for (let i = 0; i < size; i++) {
        verticalSymbols.push(verticalEdges.slice(i * (size - 1), (i + 1) * (size - 1)));
    }

    const horizontalSymbols = [];
    for (let i = 0; i < size - 1; i++) {
        horizontalSymbols.push(horizontalEdges.slice(i * size, (i + 1) * size));
    }

    return {verticalSymbols, horizontalSymbols};
}

function createBoard(size, numberOfSymbols) {
    if (numberOfSymbols > numberOfColorsThatFitInABoard(size)) {
        numberOfSymbols = numberOfColorsThatFitInABoard(size);
    }

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

function shuffleAndRotateBoard(board) {
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

function convertToPieces(board) {
    return board.flat().map(piece => ({
        top: parseInt(piece.top, 2) === 0 ? 65535 : parseInt(piece.top, 2),
        right: parseInt(piece.right, 2) === 0 ? 65535 : parseInt(piece.right, 2),
        bottom: parseInt(piece.bottom, 2) === 0 ? 65535 : parseInt(piece.bottom, 2),
        left: parseInt(piece.left, 2) === 0 ? 65535 : parseInt(piece.left, 2),
    }));
}

function exportPuzzleToCSV(pieces, boardSize, hints = []) {
    const lines = [];

    // First line: board size
    lines.push(boardSize.toString());

    // Create a map of hint indices for quick lookup
    const hintMap = new Map();
    hints.forEach(hint => {
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
        const hintX = hint?.x !== undefined ? hint.x : x;
        const hintY = hint?.y !== undefined ? hint.y : y;
        const rotation = hint?.rotation || 0;

        // Convert numeric values to binary strings (16 bits)
        const toBinary = (value) => {
            if (value === 65535) {
                return "1111111111111111"; // Border value
            }
            return value.toString(2).padStart(16, '0');
        };

        const top = toBinary(piece.top);
        const right = toBinary(piece.right);
        const bottom = toBinary(piece.bottom);
        const left = toBinary(piece.left);

        const exportX = isHint ? hintX : x;
        const exportY = isHint ? hintY : y;
        lines.push(`${top},${right},${bottom},${left},${isHint},${exportX},${exportY},${rotation},0,0`);
    }

    return lines.join('\n');
}

function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

function generatePuzzle(size, colors) {
    const board = createBoard(size, colors);
    const shuffledBoard = shuffleAndRotateBoard(board);
    const pieces = convertToPieces(shuffledBoard);

    // Shuffle the piece order so they're not in grid positions
    const shuffledPieces = shuffleArray(pieces);

    return shuffledPieces;
}

function generateHash() {
    return crypto.randomBytes(4).toString('hex');
}

function parseRange(rangeStr) {
    if (rangeStr.includes('-')) {
        const parts = rangeStr.split('-');
        return {
            min: parseInt(parts[0], 10),
            max: parseInt(parts[1], 10)
        };
    } else {
        const val = parseInt(rangeStr, 10);
        return { min: val, max: val };
    }
}

function parseArgs() {
    const args = process.argv.slice(2);
    const options = {
        sizeMin: 4,
        sizeMax: 4,
        colorsMin: 8,
        colorsMax: 8,
        count: 1,
        output: './data/generated',
        official: false,
        allCombinations: false
    };

    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        switch (arg) {
            case '--size':
            case '-s': {
                const range = parseRange(args[++i]);
                options.sizeMin = range.min;
                options.sizeMax = range.max;
                break;
            }
            case '--colors':
            case '-c': {
                const range = parseRange(args[++i]);
                options.colorsMin = range.min;
                options.colorsMax = range.max;
                break;
            }
            case '--count':
            case '-n':
                options.count = parseInt(args[++i], 10);
                break;
            case '--output':
            case '-o':
                options.output = args[++i];
                break;
            case '--official':
                options.official = true;
                break;
            case '--all-combinations':
                options.allCombinations = true;
                break;
            case '--help':
            case '-h':
                console.log(`
Puzzle Generator

Usage:
  node generate_puzzles.js [options]

Options:
  --size, -s <number|range>     Board size or range (e.g., 4 or 4-8) (default: 4)
  --colors, -c <number|range>   Number of colors or range (e.g., 8 or 6-12) (default: 8)
  --count, -n <number>          Number of puzzles to generate (default: 1)
                                Ignored when --all-combinations is used
  --output, -o <path>           Output directory (default: ./data/generated)
  --official                    Mark puzzle as "official" in filename
  --all-combinations            Generate one puzzle for each size/color combination
  --help, -h                    Show this help message

Examples:
  # Generate a single 4x4 puzzle with 8 colors
  node generate_puzzles.js --size 4 --colors 8

  # Generate 5 puzzles with sizes 4-8 and colors 6-12 (random combinations)
  node generate_puzzles.js --size 4-8 --colors 6-12 --count 5

  # Generate all combinations of sizes 4-6 and colors 8-10
  node generate_puzzles.js --size 4-6 --colors 8-10 --all-combinations

  # Generate 10 puzzles with size 7 and colors ranging from 10-14
  node generate_puzzles.js -s 7 -c 10-14 -n 10 -o ./my_puzzles

  # Generate an "official" puzzle for each size 4-8 with max colors
  node generate_puzzles.js --size 4-8 --official --all-combinations

File Format:
  size_<size>_colors_<colors>_<hash>.csv
  or
  size_<size>_official_<hash>.csv (when --official flag is used)
`);
                process.exit(0);
                break;
            default:
                console.error(`Unknown option: ${arg}`);
                console.log('Use --help for usage information');
                process.exit(1);
        }
    }

    return options;
}

function validateOptions(options) {
    const errors = [];

    if (isNaN(options.sizeMin) || isNaN(options.sizeMax)) {
        errors.push('Size must be a valid number or range');
    } else {
        if (options.sizeMin < 2 || options.sizeMin > 16) {
            errors.push('Minimum size must be between 2 and 16');
        }
        if (options.sizeMax < 2 || options.sizeMax > 16) {
            errors.push('Maximum size must be between 2 and 16');
        }
        if (options.sizeMin > options.sizeMax) {
            errors.push('Minimum size cannot be greater than maximum size');
        }
    }

    if (isNaN(options.colorsMin) || isNaN(options.colorsMax)) {
        errors.push('Colors must be a valid number or range');
    } else {
        if (options.colorsMin < 2) {
            errors.push('Minimum colors must be at least 2');
        }
        if (options.colorsMin > options.colorsMax) {
            errors.push('Minimum colors cannot be greater than maximum colors');
        }
        // Validate against max possible colors for the largest size
        const maxPossibleColors = numberOfColorsThatFitInABoard(options.sizeMax);
        if (options.colorsMax > maxPossibleColors) {
            errors.push(`Maximum colors (${options.colorsMax}) exceeds limit for size ${options.sizeMax} (max: ${maxPossibleColors})`);
        }
    }

    if (isNaN(options.count) || options.count < 1) {
        errors.push('Count must be at least 1');
    }

    if (!options.output) {
        errors.push('Output directory must be specified');
    }

    return errors;
}

function generatePuzzleConfigurations(options) {
    const configurations = [];

    if (options.allCombinations) {
        // Generate all combinations of sizes and colors
        for (let size = options.sizeMin; size <= options.sizeMax; size++) {
            const maxColors = options.official
                ? numberOfColorsThatFitInABoard(size)
                : Math.min(options.colorsMax, numberOfColorsThatFitInABoard(size));

            if (options.official) {
                // For official, generate one puzzle per size with max colors
                configurations.push({ size, colors: maxColors });
            } else {
                // Generate one for each color value in range
                for (let colors = options.colorsMin; colors <= maxColors; colors++) {
                    configurations.push({ size, colors });
                }
            }
        }
    } else {
        // Generate random configurations
        for (let i = 0; i < options.count; i++) {
            const size = options.sizeMin === options.sizeMax
                ? options.sizeMin
                : Math.floor(Math.random() * (options.sizeMax - options.sizeMin + 1)) + options.sizeMin;

            const maxColorsForSize = numberOfColorsThatFitInABoard(size);
            const effectiveMaxColors = Math.min(options.colorsMax, maxColorsForSize);

            const colors = options.official
                ? maxColorsForSize
                : (options.colorsMin === effectiveMaxColors
                    ? options.colorsMin
                    : Math.floor(Math.random() * (effectiveMaxColors - options.colorsMin + 1)) + options.colorsMin);

            configurations.push({ size, colors });
        }
    }

    return configurations;
}

function main() {
    const options = parseArgs();
    const errors = validateOptions(options);

    if (errors.length > 0) {
        console.error('Validation errors:');
        errors.forEach(err => console.error(`  - ${err}`));
        process.exit(1);
    }

    // Create output directory if it doesn't exist
    if (!fs.existsSync(options.output)) {
        fs.mkdirSync(options.output, { recursive: true });
        console.log(`Created output directory: ${options.output}`);
    }

    // Generate puzzle configurations
    const configurations = generatePuzzleConfigurations(options);

    console.log(`Generating ${configurations.length} puzzle(s)...`);
    if (options.sizeMin === options.sizeMax) {
        console.log(`  Size: ${options.sizeMin}x${options.sizeMin}`);
    } else {
        console.log(`  Size range: ${options.sizeMin}x${options.sizeMin} to ${options.sizeMax}x${options.sizeMax}`);
    }
    if (options.colorsMin === options.colorsMax && !options.official) {
        console.log(`  Colors: ${options.colorsMin}`);
    } else if (!options.official) {
        console.log(`  Colors range: ${options.colorsMin} to ${options.colorsMax}`);
    }
    if (options.official) {
        console.log(`  Mode: Official (max colors for each size)`);
    }
    console.log(`  Output: ${options.output}`);
    console.log();

    const generatedFiles = [];

    for (let i = 0; i < configurations.length; i++) {
        const { size, colors } = configurations[i];

        // Generate puzzle
        const pieces = generatePuzzle(size, colors);
        const csvContent = exportPuzzleToCSV(pieces, size);

        // Generate filename
        const hash = generateHash();
        const colorPart = options.official ? 'official' : `colors_${colors}`;
        const filename = `size_${size}_${colorPart}_${hash}.csv`;
        const filepath = path.join(options.output, filename);

        // Write to file
        fs.writeFileSync(filepath, csvContent);
        generatedFiles.push(filename);

        console.log(`  [${i + 1}/${configurations.length}] Generated: ${filename} (${size}x${size}, ${colors} colors)`);
    }

    console.log();
    console.log(`Successfully generated ${generatedFiles.length} puzzle(s)!`);
}

// Run the script
if (require.main === module) {
    main();
}

module.exports = {
    generatePuzzle,
    exportPuzzleToCSV,
    createBoard,
    shuffleAndRotateBoard,
    convertToPieces
};
