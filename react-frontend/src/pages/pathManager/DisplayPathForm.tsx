import {SyntheticEvent} from 'react';
import {Path, pathsState} from "../requestForm/atoms.ts";
import {Autocomplete, Button, FormGroup, Slider, TextField, Typography} from "@mui/material";
import {useRecoilState} from "recoil";
import Box from "@mui/material/Box";
import {
    boardSizeState,
    DEFAULT_SELECTED_CELLS,
    displayedCellsState,
    GRID_SIZE_DEFAULT,
    GRID_SIZE_MAX,
    GRID_SIZE_MIN,
    selectedCellsState
} from "./atom.ts";
import {convertPathToSelectedCells} from "./utils.ts";

export const DisplayPathForm = () => {
    const paths = useRecoilState(pathsState)[0];

    // States used by path manager
    const [boardSize, setBoardSize] = useRecoilState(boardSizeState);
    const setDisplayedCells = useRecoilState(displayedCellsState)[1];
    const setSelectedCells = useRecoilState(selectedCellsState)[1];

    const resetGrid = () => {
        setDisplayedCells(DEFAULT_SELECTED_CELLS);
        setSelectedCells(DEFAULT_SELECTED_CELLS);
    }

    const toBeImplemented = () => {
    }

    const availablePaths = paths.filter(path => path.path.length === boardSize ** 2);

    const handlePathChange = (_: SyntheticEvent<Element, Event>, value: Path | null) => {
        if (value) {
            setSelectedCells([...DEFAULT_SELECTED_CELLS, ...convertPathToSelectedCells(value.path)]);
            setDisplayedCells([...DEFAULT_SELECTED_CELLS, ...convertPathToSelectedCells(value.path)]);
        }
    }

    return (
        <FormGroup style={{width: '80%'}}>
            <Typography id="input-slider-path" gutterBottom>
                Select Path
            </Typography>
            <Slider
                defaultValue={GRID_SIZE_DEFAULT}
                min={GRID_SIZE_MIN}
                max={GRID_SIZE_MAX}
                value={boardSize}
                onChange={
                    (_, value) => {
                        setBoardSize(value as number)
                        resetGrid()
                    }
                }
                marks
                step={1}
                aria-labelledby={"input-slider-path"}
                valueLabelDisplay="on"
            />
            <Autocomplete
                id="available-paths"
                options={availablePaths}
                getOptionLabel={(option) => option.label}
                onChange={handlePathChange}
                renderInput={(params) => <TextField {...params} label="Available Paths"/>}
            />
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                width: '100%',
                marginTop: '20px',
                marginBottom: '20px',
            }}>
                <Box display="flex" justifyContent="space-between" width="80%">
                    <Button variant="outlined" color="error" onClick={toBeImplemented}>
                        Delete Path
                    </Button>
                    <Button variant="outlined" onClick={toBeImplemented}>
                        Animate Path
                    </Button>
                </Box>
            </div>
        </FormGroup>
    );
}
