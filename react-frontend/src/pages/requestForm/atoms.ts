import {atom} from "recoil";


export const settingsState = atom({
    key: 'settingsState', // unique ID (with respect to other atoms/selectors)
    default: {
        boardSize: 0,
        boardColors: 0,
        paths: '',
        useCache: false,
    }, // default value (aka initial value)
});


