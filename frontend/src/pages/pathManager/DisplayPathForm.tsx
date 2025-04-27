import { useState } from "react";
import { Box, Button, Grid, Typography } from "@mui/material";
import { useRecoilState } from "recoil";
import { pathsState } from "../requestForm/atoms.ts";

export const DisplayPathForm = () => {
    const [paths, setPaths] = useRecoilState(pathsState);
    const [selectedPath, setSelectedPath] = useState<number | null>(null);

    const handleDeletePath = (index: number) => {
        const newPaths = paths.filter((_, i) => i !== index);
        setPaths(newPaths);
        if (selectedPath === index) {
            setSelectedPath(null);
        }
    };

    return (
        <Box sx={{ width: '100%', maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
            <Typography variant="h6" gutterBottom>
                Saved Paths
            </Typography>
            <Grid container spacing={2}>
                {paths.map((path, index) => (
                    <Grid item xs={12} key={index}>
                        <Box sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px',
                            border: '1px solid #ddd',
                            borderRadius: '4px'
                        }}>
                            <Typography>
                                {path.label} ({path.path.length} cells)
                            </Typography>
                            <Button
                                variant="contained"
                                color="error"
                                onClick={() => handleDeletePath(index)}
                            >
                                Delete
                            </Button>
                        </Box>
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
};
