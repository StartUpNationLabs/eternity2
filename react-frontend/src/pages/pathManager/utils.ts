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
