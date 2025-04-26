import {Grid} from "@mui/material";
import PathManagerGrid from "./PathManagerGrid.tsx";
import {PathManagerTabs} from "./PathManagerTabs.tsx";


function PathManager() {
    return (
        <Grid container spacing={2}
              style={{height: '90vh', display: 'flex', justifyContent: 'center', paddingTop: '5vh'}}>
            <Grid item xs={6}>
                <div style={{
                    alignItems: 'center',
                    width: '80%',
                    height: '80%',
                    margin: 'auto',
                }}>
                    <PathManagerTabs></PathManagerTabs>
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
                    <PathManagerGrid/>
                </div>
            </Grid>
        </Grid>
    )
}

export default PathManager;
