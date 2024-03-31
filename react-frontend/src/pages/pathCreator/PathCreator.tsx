import React, {useState} from "react";
import {useRecoilState} from "recoil";
import {settingsState} from "../requestForm/atoms.ts";
import {Grid} from "@mui/material";
import GridSelector from "./GridSelector.tsx";
import {PathCreatorForm} from "./PathCreatorForm.tsx";


function PathCreator() {
    const [settings, setSettings] = useRecoilState(settingsState);
    const [boardSize, setBoardSize] = useState(10);
    const [pathName, setPathName] = useState('');
    const [path, setPath] = useState([]);

    return (
        <Grid container spacing={2}
              style={{height: '90vh', display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
            <Grid item xs={6}>
                <div style={{
                    justifyContent: 'center',
                    alignItems: 'center',
                    width: '80%',
                    height: '80%',
                    margin: 'auto',
                }}>
                    <PathCreatorForm></PathCreatorForm>
                </div>
            </Grid>
            <Grid item xs={6}>
                <div style={{
                    justifyContent: 'center',
                    alignItems: 'center',
                    width: '80%',
                    height: '80%',
                    margin: 'auto',
                }}>
                    <GridSelector/>
                </div>
            </Grid>
        </Grid>
    )
}

export default PathCreator;
