import { useState } from "react";
import { Box, Button, Grid, TextField, Typography } from "@mui/material";
import { useRecoilState } from "recoil";
import { pathsState } from "../requestForm/atoms.ts";

export const CreatePathForm = () => {
    const [paths, setPaths] = useRecoilState(pathsState);
    const [pathName, setPathName] = useState("");

    const handlePathNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setPathName(event.target.value);
    };

    const handleSavePath = () => {
        if (pathName.trim() === "") return;

        setPaths([...paths, {
            path: [],
            label: pathName
        }]);
        setPathName("");
    };

    return (
        <Box sx={{ width: '100%', maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
            <Typography variant="h6" gutterBottom>
                Create New Path
            </Typography>
            <Grid container spacing={2}>
                <Grid item xs={12}>
                    <TextField
                        fullWidth
                        label="Path Name"
                        value={pathName}
                        onChange={handlePathNameChange}
                    />
                </Grid>
                <Grid item xs={12}>
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleSavePath}
                        disabled={pathName.trim() === ""}
                    >
                        Save Path
                    </Button>
                </Grid>
            </Grid>
        </Box>
    );
};
