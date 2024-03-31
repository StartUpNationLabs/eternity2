import {atom} from "recoil";
import {BOARD_SIZE_DEFAULT} from "../../utils/Constants.tsx";

export const DEFAULT_SELECTED_CELLS = [0] as number[];

export const boardSizeState = atom({
    key: 'boardSizeState',
    default: BOARD_SIZE_DEFAULT as number,
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
