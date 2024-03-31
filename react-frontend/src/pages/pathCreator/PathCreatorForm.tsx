// src/pages/pathCreator/PathCreatorForm.tsx
import * as React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import {CreatePathForm} from "./CreatePathForm.tsx";
import {DisplayPathForm} from "./DisplayPathForm.tsx";


export const PathCreatorForm = () => {
    const [value, setValue] = React.useState(0);

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setValue(newValue);
    };

    return (
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px solid white'}}>
            <Tabs value={value} onChange={handleChange} aria-label="custom tabs example">
                <Tab label="Create path"/>
                <Tab label="See existing paths"/>
            </Tabs>
            {value === 0 && <CreatePathForm/>}
            {value === 1 && <DisplayPathForm/>}
        </div>
    );
}
