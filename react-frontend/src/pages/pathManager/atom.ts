import {atom} from "recoil";

export const DEFAULT_SELECTED_CELLS = [0] as number[];
export const GRID_SIZE_MIN = 2;
export const GRID_SIZE_MAX = 16;
export const GRID_SIZE_DEFAULT = 4;

export const pathManagerState = atom({
    key: 'pathManagerState',
    default: {
        // Common
        boardSize: 4,
        displayedCells: [] as number[],
        // Create Path
        selectedCells: [0] as number[],
        // Display Path
        selectedPath: [] as number[],
        selectedPathName: '',
    }
});

export const boardSizeState = atom({
    key: 'boardSizeState',
    default: 4,
});


export const displayedCellsState = atom({
    key: 'displayedCellsState',
    default: DEFAULT_SELECTED_CELLS as number[],
});

export const selectedCellsState = atom({
    key: 'selectedCellsState',
    default: DEFAULT_SELECTED_CELLS as number[],
});

export const selectedPathState = atom({
    key: 'selectedPathState',
    default: [] as number[],
});

export const selectedPathNameState = atom({
    key: 'selectedPathNameState',
    default: '',
});
