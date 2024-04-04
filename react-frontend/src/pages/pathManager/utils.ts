export enum Movement {
    Up = 'up',
    Down = 'down',
    Left = 'left',
    Right = 'right',
    UpLeft = 'up-left',
    UpRight = 'up-right',
    DownLeft = 'down-left',
    DownRight = 'down-right'
}

export function convertSelectedCellsToPath(inputCells: number[]) {
    const rearrangedCells = [];

    // Selected cells: 0, 1, 2, 3, 7, 11, 15, 14, 13, 12, 8, 4, 5, 6, 10, 9
    // Path: 1, 2, 3, 7, 5, 6, 10, 11, 4, 2147483647, 9, 15, 8, 12, 13, 14

    // Fill the new list with 0s
    for (let i = 0; i < inputCells.length; i++) {
        rearrangedCells.push(0);
    }

    for (let i = 0; i < inputCells.length; i++) {
        if (i === inputCells.length - 1) {
            rearrangedCells[inputCells[i]] = 2147483647;
            break;
        }
        rearrangedCells[inputCells[i]] = inputCells[i + 1];
    }

    return rearrangedCells;
}

export function convertPathToSelectedCells(path: number[]) {
    const selectedCells = [];

    // Path: 1, 2, 3, 7, 5, 6, 10, 11, 4, 2147483647, 9, 15, 8, 12, 13, 14
    // Selected cells from path: 0, 1, 2, 3, 7, 11, 15, 14, 13, 12, 8, 4, 5, 6, 10, 9

    let nextCell = path[0];

    while (nextCell !== 2147483647) {
        selectedCells.push(nextCell);
        nextCell = path[nextCell];
    }

    return selectedCells;
}

// Function to map rank to color gradient between dark blue and light blue (excluding 10% at both ends)
export function rankToColor(boardSize: number, rank: number) {
    const limitPercentage = 0.8;
    const numberOfSteps = boardSize * boardSize;
    const baseColorR = Math.floor(255 * limitPercentage);
    const baseColorG = 0;
    const baseColorB = 0;

    // Adjust the range to exclude the extreme 10% colors
    const adjustedRange = 255 * 0.1 * (numberOfSteps / (numberOfSteps - 2));

    // Only range across blue and red
    const colorR = Math.floor(baseColorR - (baseColorR * rank / numberOfSteps) - adjustedRange);
    const colorG = Math.floor(baseColorG + (255 * rank / numberOfSteps) - adjustedRange);
    const colorB = Math.floor(baseColorB + (255 * rank / numberOfSteps) - adjustedRange);

    return `rgb(${colorR}, ${colorG}, ${colorB})`;
}

// Function to calculate direction of selection based on current and last cell id
export function calculateDirection(boardSize: number, currentCellId: number, lastCellId: number | null): Movement | null {
    if (lastCellId === null) return null;

    const rowDiff = Math.floor(currentCellId / boardSize) - Math.floor(lastCellId / boardSize);
    const colDiff = currentCellId % boardSize - lastCellId % boardSize;
    if (rowDiff === -1 && colDiff === 0) return Movement.Up;
    if (rowDiff === 1 && colDiff === 0) return Movement.Down;
    if (rowDiff === 0 && colDiff === -1) return Movement.Left;
    if (rowDiff === 0 && colDiff === 1) return Movement.Right;
    if (rowDiff === -1 && colDiff === -1) return Movement.UpLeft;
    if (rowDiff === -1 && colDiff === 1) return Movement.UpRight;
    if (rowDiff === 1 && colDiff === -1) return Movement.DownLeft;
    if (rowDiff === 1 && colDiff === 1) return Movement.DownRight;

    return null;
};
