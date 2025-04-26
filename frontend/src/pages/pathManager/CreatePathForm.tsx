import * as React from 'react';
import {hintTemplatesState, pathsState} from "../requestForm/atoms.ts";
import {FormGroup, Slider, TextField, Typography} from "@mui/material";
import {useRecoilState} from "recoil";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import {boardSizeState, DEFAULT_SELECTED_CELLS, hintCellsState, selectedCellsState} from "./atom.ts";
import {convertSelectedCellsToPath} from "./utils.ts"
import {BOARD_SIZE_DEFAULT, BOARD_SIZE_MAX, BOARD_SIZE_MIN, BOARD_SIZE_STEP} from "../../utils/Constants.tsx";

export const CreatePathForm = () => {
    // Available paths on the website
    const [paths, setPaths] = useRecoilState(pathsState);
    const [hints, setHints] = useRecoilState(hintTemplatesState);
    // User input for path name
    const [pathName, setPathName] = React.useState('');
    // State variable for showing the success message
    const [showSuccessMessage, setShowSuccessMessage] = React.useState(false);

    // States used by path manager
    const [boardSize, setBoardSize] = useRecoilState(boardSizeState);
    const [selectedCells, setSelectedCells] = useRecoilState(selectedCellsState);
    const [hintCells, setHintCells] = useRecoilState(hintCellsState);

    // ===== Reset ==== //

    const resetSelectedCells = () => {
        setSelectedCells(DEFAULT_SELECTED_CELLS);
    };

    const resetHintCells = () => {
        setHintCells([]);
    }

    const resetGrid = () => {
        resetSelectedCells();
        resetHintCells();
    }

    // ===== Path ==== //
    console.log(hints);

    const handlePathNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setPathName(event.target.value);
    };

    const isSavePathDisabled = () => {
        return pathName === '' ||
            selectedCells.length !== boardSize ** 2 ||
            paths.some(path => path.label === pathName && path.path.length === boardSize ** 2);
    };

    const handleSavePath = () => {
        const hintsIndex = hintCells.length > 0 ? hintCells : [];

        // Create hint objects from the hint cells

        setPaths([...paths, {
            path: convertSelectedCellsToPath(selectedCells),
            label: pathName,
        }]);
        setHints([...hints, {
            pieceIndex: hintsIndex,
            boardSize: boardSize * boardSize,
            label: pathName,
        }]);
        resetGrid();
        setPathName('');

        // Show the success message and hide it after 3 seconds
        setShowSuccessMessage(true);
        setTimeout(() => setShowSuccessMessage(false), 3000);
    };

    // ===== Render ==== //

    return (
        <FormGroup sx={{
            width: '100%',
            maxWidth: '800px',
            margin: '0 auto',
            padding: '20px'
        }}>
            <Typography id="input-slider-size" gutterBottom variant="h6">
                Board size
            </Typography>
            <Slider
                defaultValue={BOARD_SIZE_DEFAULT}
                min={BOARD_SIZE_MIN}
                max={BOARD_SIZE_MAX}
                value={boardSize}
                onChange={(_, v) => {
                    setBoardSize(v as number)
                    resetGrid()
                }}
                marks
                step={BOARD_SIZE_STEP}
                aria-labelledby={"input-slider-size"}
                valueLabelDisplay="on"
                sx={{ mb: 3 }}
            />
            <TextField 
                id="path-name-input" 
                label="Path Name" 
                variant="outlined" 
                value={pathName}
                onChange={handlePathNameChange}
                sx={{ width: '100%', mb: 3 }}
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
                        onClick={resetGrid}
                        sx={{ flex: 1 }}
                    >
                        Reset path
                    </Button>
                    <Button 
                        variant="outlined" 
                        disabled={true}
                        sx={{ flex: 1 }}
                    >
                        Animate path (TODO)
                    </Button>
                    <Button 
                        variant="contained" 
                        color="success" 
                        disabled={isSavePathDisabled()}
                        onClick={handleSavePath}
                        sx={{ flex: 1 }}
                    >
                        Save path
                    </Button>
                </Box>
            </Box>
            <Box sx={{
                display: 'flex',
                justifyContent: 'center',
                width: '100%'
            }}>
                {showSuccessMessage ? (
                    <Typography variant="body2" color="success">
                        Path has been saved successfully.
                    </Typography>
                ) : isSavePathDisabled() && (
                    <Typography variant="body2" color="error">
                        A new path must have a name and cover the full board in order to be saved.
                    </Typography>
                )}
            </Box>
        </FormGroup>
    );
}
