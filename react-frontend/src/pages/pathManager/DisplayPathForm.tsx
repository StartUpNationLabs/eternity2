import {SyntheticEvent} from 'react';
import {Path, pathsState} from "../requestForm/atoms.ts";
import {Autocomplete, Button, FormGroup, Slider, TextField, Typography} from "@mui/material";
import {useRecoilState} from "recoil";
import Box from "@mui/material/Box";
import {
    boardSizeState,
    DEFAULT_SELECTED_CELLS,
    displayedCellsState,
    selectedCellsState,
    selectedPathState
} from "./atom.ts";
import {convertPathToSelectedCells} from "./utils.ts";
import {BOARD_SIZE_DEFAULT, BOARD_SIZE_MAX, BOARD_SIZE_MIN, BOARD_SIZE_STEP} from "../../utils/Constants.tsx";

export const DisplayPathForm = () => {
    const paths = useRecoilState(pathsState)[0];

    // States used by path manager
    const [boardSize, setBoardSize] = useRecoilState(boardSizeState);
    const setDisplayedCells = useRecoilState(displayedCellsState)[1];
    const setSelectedCells = useRecoilState(selectedCellsState)[1];
    const [selectedPath, setSelectedPath] = useRecoilState(selectedPathState);

    const resetGrid = () => {
        setDisplayedCells(DEFAULT_SELECTED_CELLS);
        setSelectedCells(DEFAULT_SELECTED_CELLS);
    }

    const toBeImplemented = () => {
    }

    const availablePaths = paths.filter(path => path.path.length === boardSize ** 2);

    const handleBoardSizeChange = (_: Event, value: number | number[]) => {
        if (typeof value === 'number') {
            setBoardSize(value);

            // If there is a path selected, and a path for the new board size is available, choose this path and display it
            const filteredPaths = paths.filter(path => path.path.length === value ** 2).filter(path => path.label === selectedPath?.label);
            if (filteredPaths.length > 0) {
                setSelectedPath(filteredPaths[0]);
                setSelectedCells([...DEFAULT_SELECTED_CELLS, ...convertPathToSelectedCells(filteredPaths[0].path)]);
                setDisplayedCells([...DEFAULT_SELECTED_CELLS, ...convertPathToSelectedCells(filteredPaths[0].path)]);
            } else {
                setSelectedPath(null);
                resetGrid();
            }
        }
    }

    const handlePathChange = (_: SyntheticEvent<Element, Event>, value: Path | null) => {
        if (value) {
            setSelectedPath(value);
            setSelectedCells([...DEFAULT_SELECTED_CELLS, ...convertPathToSelectedCells(value.path)]);
            setDisplayedCells([...DEFAULT_SELECTED_CELLS, ...convertPathToSelectedCells(value.path)]);
        } else {
            setSelectedPath(null);
            resetGrid();
        }
    }

    return (
        <FormGroup style={{width: '80%'}}>
            <Typography id="input-slider-path" gutterBottom>
                Select Path
            </Typography>
            <Slider
                defaultValue={BOARD_SIZE_DEFAULT}
                min={BOARD_SIZE_MIN}
                max={BOARD_SIZE_MAX}
                value={boardSize}
                onChange={handleBoardSizeChange}
                marks
                step={BOARD_SIZE_STEP}
                aria-labelledby={"input-slider-path"}
                valueLabelDisplay="on"
            />
            <Autocomplete
                id="available-paths"
                options={availablePaths}
                getOptionLabel={(option) => option.label}
                onChange={handlePathChange}
                value={selectedPath}
                renderInput={(params) => <TextField {...params} label="Available Paths"/>}
                style={{marginTop: '20px'}}
            />
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                width: '100%',
                marginTop: '20px',
                marginBottom: '20px',
            }}>
                <Box display="flex" justifyContent="space-between" width="50%">
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
