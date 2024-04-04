import * as React from 'react';
import {hintsState, pathsState} from "../requestForm/atoms.ts";
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
    // Hints for the current path
    const setHints = useRecoilState(hintsState)[1];
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
        // Hint : {index: number, x: number, y: number, rotation: number}
        const hints = hintsIndex.map(index => ({
            index: index,
            x: index % boardSize,
            y: Math.floor(index / boardSize),
            rotation: 0,
        }));

        setPaths([...paths, {
            path: convertSelectedCellsToPath(selectedCells),
            label: pathName,
        }]);
        setHints([...hints])

        resetGrid();
        setPathName('');

        // Show the success message and hide it after 3 seconds
        setShowSuccessMessage(true);
        setTimeout(() => setShowSuccessMessage(false), 3000);
    };

    // ===== Render ==== //

    return (
        <FormGroup style={{width: '80%'}}>
            <Typography id="input-slider-size" gutterBottom>
                Board size
            </Typography>
            <Slider
                defaultValue={BOARD_SIZE_DEFAULT}
                min={BOARD_SIZE_MIN}
                max={BOARD_SIZE_MAX}
                value={
                    boardSize
                }
                onChange={
                    (_, v) => {
                        setBoardSize(v as number)
                        resetGrid()
                    }
                }
                marks
                step={BOARD_SIZE_STEP}
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
                    <Button variant="outlined" color="error" onClick={resetGrid}>
                        Reset path
                    </Button>
                    <Button variant="outlined" disabled={true}>
                        Animate path (TODO)
                    </Button>
                    <Button variant="contained" color="success" disabled={isSavePathDisabled()}
                            onClick={handleSavePath}>
                        Save path
                    </Button>
                </Box>
            </div>
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                width: '100%',
                marginBottom: '20px'
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
            </div>
        </FormGroup>
    );
}
