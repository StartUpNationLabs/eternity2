import * as React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import {CreatePathForm} from "./CreatePathForm.tsx";
import {DisplayPathForm} from "./DisplayPathForm.tsx";
import {useRecoilState} from "recoil";
import {DEFAULT_SELECTED_CELLS, hintCellsState, selectedCellsState} from "./atom.ts";


export const PathManagerTabs = () => {
    const [value, setValue] = React.useState(0);
    const setSelectedCells = useRecoilState(selectedCellsState)[1];
    const setHintCells = useRecoilState(hintCellsState)[1];

    const resetGrid = () => {
        setSelectedCells(DEFAULT_SELECTED_CELLS);
        setHintCells([])
    }

    const handleChange = (_: React.SyntheticEvent, newValue: number) => {
        setValue(newValue);
        resetGrid();
    };

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
        }}>
            <Tabs value={value} onChange={handleChange} aria-label="custom tabs example">
                <Tab label="Create path"/>
                <Tab label="See existing paths"/>
            </Tabs>
            {value === 0 && <CreatePathForm/>}
            {value === 1 && <DisplayPathForm/>}
        </div>
    );
}
