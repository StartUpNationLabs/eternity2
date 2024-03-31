import {atom} from "recoil";

export const gridSelectorState = atom({
    key: 'gridSelectorState',
    default: {
        boardSize: 4,
        selectedCells: [] as number[],
    }
});
