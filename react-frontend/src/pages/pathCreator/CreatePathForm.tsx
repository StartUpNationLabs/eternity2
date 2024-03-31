import * as React from 'react';
import {gridSelectorState, pathsState} from "../requestForm/atoms.ts";
import {Slider, TextField, Typography} from "@mui/material";
import {useRecoilState} from "recoil";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";

export const CreatePathForm = () => {
    const [gridSelector, setGridSelectorState] = useRecoilState(gridSelectorState);
    const [paths, setPaths] = useRecoilState(pathsState);
    const [pathName, setPathName] = React.useState(''); // Add state for path name

    const handlePathNameChange = (event) => { // Add function to handle changes to the input field
        setPathName(event.target.value);
    };

    function getNextCells(selectedCells: number[]): number[] {
        console.log("Get next cells")
        console.log(selectedCells)
        const nextCells = selectedCells.map((_, index) => {
            if (index < selectedCells.length - 1) {
                return selectedCells[index + 1];
            } else {
                return 2147483647;
            }
        });
        console.log(nextCells)

        return nextCells;
    }

    return (
        <div style={{width: '80%'}}>
            <Typography id="input-slider-size" gutterBottom>
                Board size
            </Typography>
            <Slider
                defaultValue={4}
                min={2}
                max={16}
                value={
                    gridSelector.boardSize
                }
                onChange={
                    (_, v) => {
                        setGridSelectorState({
                            ...gridSelector, boardSize: v as number, selectedCells: [] as number[]
                        })
                    }
                }
                marks
                step={1}
                aria-labelledby={"input-slider-size"}
                valueLabelDisplay="on"
            />
            <div style={{marginTop: '20px', marginBottom: '20px'}}>
                <TextField id="path-name-input" label="Path Name" variant="outlined" style={{width: '100%'}}
                           value={pathName}
                           onChange={handlePathNameChange}/>
            </div>
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                width: '100%',
                marginBottom: '20px'
            }}>
                <Box display="flex" justifyContent="space-between" width="80%">
                    <Button variant="outlined" color="error"
                            onClick={() => setGridSelectorState({
                                ...gridSelector,
                                selectedCells: [] as number[]
                            })}>
                        Reset path
                    </Button>
                    <Button variant="outlined">
                        Animate path
                    </Button>
                    <Button variant="contained" color="success"
                            disabled={
                                pathName === '' || // Check if path name is empty
                                gridSelector.selectedCells.length !== gridSelector.boardSize * gridSelector.boardSize || // Check if path is complete
                                paths.some(path => path.label === pathName) // Check if path name already exists
                            }
                            onClick={() => {
                                setPaths([...paths, {
                                    path: getNextCells(gridSelector.selectedCells),
                                    label: pathName
                                }])
                                setGridSelectorState({
                                    ...gridSelector,
                                    selectedCells: [] as number[]
                                })
                                setPathName(''); // Reset the input field
                            }
                            }
                    >
                        Save path
                    </Button>
                </Box>
            </div>
        </div>
    );
}
