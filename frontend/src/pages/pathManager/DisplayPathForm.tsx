import {SyntheticEvent} from 'react';
import {pathsState} from "../requestForm/atoms.ts";
import {Autocomplete, Button, FormGroup, Slider, TextField, Typography} from "@mui/material";
import {useRecoilState} from "recoil";
import Box from "@mui/material/Box";
import {boardSizeState, DEFAULT_SELECTED_CELLS, selectedCellsState, selectedPathState} from "./atom.ts";
import {convertPathToSelectedCells} from "./utils.ts";
import {BOARD_SIZE_DEFAULT, BOARD_SIZE_MAX, BOARD_SIZE_MIN, BOARD_SIZE_STEP} from "../../utils/Constants.tsx";
import {Path} from "../../utils/interface.tsx";

export const DisplayPathForm = () => {
    const paths = useRecoilState(pathsState)[0];

    // States used by path manager
    const [boardSize, setBoardSize] = useRecoilState(boardSizeState);
    const setSelectedCells = useRecoilState(selectedCellsState)[1];
    const [selectedPath, setSelectedPath] = useRecoilState(selectedPathState);

    const resetGrid = () => {
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
        } else {
            setSelectedPath(null);
            resetGrid();
        }
    }

    return (
        <FormGroup sx={{
            width: '100%',
            maxWidth: '800px',
            margin: '0 auto',
            padding: '20px'
        }}>
            <Typography id="input-slider-path" gutterBottom variant="h6">
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
                sx={{ mb: 3 }}
            />
            <Autocomplete
                id="available-paths"
                options={availablePaths}
                getOptionLabel={(option) => option.label}
                onChange={handlePathChange}
                value={selectedPath}
                renderInput={(params) => <TextField {...params} label="Available Paths"/>}
                sx={{ mb: 3 }}
            />
            <Box sx={{
                display: 'flex',
                justifyContent: 'center',
                width: '100%',
                mb: 3
            }}>
                <Box sx={{
                    display: 'flex',
                    gap: 2,
                    width: '100%'
                }}>
                    <Button 
                        variant="outlined" 
                        color="error" 
                        onClick={toBeImplemented}
                        sx={{ flex: 1 }}
                    >
                        Delete Path
                    </Button>
                    <Button 
                        variant="outlined" 
                        disabled={true}
                        sx={{ flex: 1 }}
                    >
                        Animate path (TODO)
                    </Button>
                </Box>
            </Box>
        </FormGroup>
    );
}
