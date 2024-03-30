import {atom, RecoilState} from "recoil";


export const settingsState = atom({
    key: 'settingsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSize: 0,
        boardColors: 0,
        paths: '',
        useCache: false,
    }, // default value (aka initial value)
});


interface Path {
    label: string;
    path: number[];
}


const defaultPaths: Path[] =  [...Array(16).keys()].map(
    i => ({
        label: `Scan Row`,
        path: [...Array((i + 2) * (i + 2)).keys()].map(j => j + 1)
        ,
    })
);


console.log(defaultPaths);

export const pathsState: RecoilState<Path[]> = atom({
    key: 'pathsState',
    default: defaultPaths,
});

