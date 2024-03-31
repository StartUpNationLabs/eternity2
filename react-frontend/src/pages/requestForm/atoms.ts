import {atom, RecoilState} from "recoil";
import {SolverSolveRequest} from "../../proto/solver/v1/solver.ts";

export interface Path {
    label: string;
    path: number[];
}

export const settingsState
    = atom({
    key: 'settingsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSize: 4,
        boardColors: 4,
        path: {
            label: `Default`,
            path: [] as number[]
        },
        useCache: false,
    }, // default value (aka initial value)
});


const defaultPaths: Path[] = [...Array(16).keys()].map(
    i => ({
        label: `Scan Row`,
        path: [...Array((i + 2) * (i + 2)).keys()].map(j => j + 1)
        ,
    })
);
export const defaultPath = {
    label: "Default",
    path: []
}


export const pathsState: RecoilState<Path[]> = atom({
    key: 'pathsState',
    default: [...defaultPaths, defaultPath],
});

export const boardState: RecoilState<SolverSolveRequest["pieces"]> = atom({
    key: 'boardState',
    default: [] as SolverSolveRequest["pieces"],
});

export const gridSelectorState = atom({
    key: 'gridSelectorState',
    default: {
        boardSize: 4,
        selectedCells: [] as number[],
    }
});
