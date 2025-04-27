import * as React from 'react';
import {hintTemplatesState, pathsState} from "../requestForm/atoms.ts";
import {FormGroup, Slider, TextField, Typography, Paper} from "@mui/material";
import {useRecoilState} from "recoil";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import {boardSizeState, DEFAULT_SELECTED_CELLS, hintCellsState, selectedCellsState} from "./atom.ts";
import {convertSelectedCellsToPath} from "./utils.ts"
import {BOARD_SIZE_DEFAULT, BOARD_SIZE_MAX, BOARD_SIZE_MIN, BOARD_SIZE_STEP} from "../../utils/Constants.tsx";
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { useCallback, useState } from 'react';
import { calculateCellDelay } from "./animation.ts";
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

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

    // Animation states
    const [isAnimating, setIsAnimating] = useState(false);
    const [animationTimeout, setAnimationTimeout] = useState<NodeJS.Timeout | null>(null);

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

    // ===== Animation ==== //
    const startAnimation = useCallback(() => {
        if (selectedCells.length <= 1 || isAnimating) return;

        setIsAnimating(true);
        // Store the original path without DEFAULT_SELECTED_CELLS
        const pathToAnimate = selectedCells.filter(cell => !DEFAULT_SELECTED_CELLS.includes(cell));
        let currentIndex = 0;

        const delay = calculateCellDelay(pathToAnimate.length);

        const animate = () => {
            if (currentIndex < pathToAnimate.length) {
                // Show cells up to the current index
                const animatedPath = pathToAnimate.slice(0, currentIndex + 1);
                setSelectedCells([...DEFAULT_SELECTED_CELLS, ...animatedPath]);
                
                currentIndex++;
                const timeout = setTimeout(animate, delay);
                setAnimationTimeout(timeout);
            } else {
                setIsAnimating(false);
                setAnimationTimeout(null);
            }
        };

        animate();
    }, [selectedCells, isAnimating, setSelectedCells]);

    // Cleanup animation on unmount
    React.useEffect(() => {
        return () => {
            if (animationTimeout) {
                clearTimeout(animationTimeout);
            }
        };
    }, [animationTimeout]);

    // ===== Path ==== //
    const handlePathNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setPathName(event.target.value);
    };

    const isSavePathDisabled = () => {
        return pathName === '' ||
            selectedCells.length !== boardSize ** 2 ||
            paths.some(path => path.label === pathName && path.path.length === boardSize ** 2);
    };

    const isAnimateDisabled = () => {
        return selectedCells.length <= 1 || isAnimating;
    };

    const handleSavePath = () => {
        const hintsIndex = hintCells.length > 0 ? hintCells : [];

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

        setShowSuccessMessage(true);
    };

    const handleCloseSnackbar = (event?: React.SyntheticEvent | Event, reason?: string) => {
        if (reason === 'clickaway') {
            return;
        }
        setShowSuccessMessage(false);
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

            {/* Help Section */}
            <Paper elevation={1} sx={{ p: 2, mb: 2, bgcolor: 'background.default' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <HelpOutlineIcon sx={{ mr: 1 }} />
                    <Typography variant="h6" component="h2">
                        How to Create a Path
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    <Typography variant="body2">
                        <strong>Left Click:</strong> Select a cell to add it to your path
                    </Typography>
                    <Typography variant="body2">
                        <strong>Left Click + Drag:</strong> Select multiple cells in a line
                    </Typography>
                    <Typography variant="body2">
                        <strong>Right Click:</strong> Mark a cell as a hint (turns green)
                    </Typography>
                    <Typography variant="body2">
                        <strong>Right Click Again:</strong> Remove hint from a cell
                    </Typography>
                </Box>
            </Paper>

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
                        variant="contained"
                        color="error" 
                        onClick={resetGrid}
                        sx={{ 
                            flex: 1,
                            bgcolor: 'error.main',
                            '&:hover': {
                                bgcolor: 'error.dark',
                            }
                        }}
                    >
                        Reset path
                    </Button>
                    <Button 
                        variant="contained"
                        color="primary"
                        onClick={startAnimation}
                        disabled={isAnimateDisabled()}
                        startIcon={<PlayArrowIcon />}
                        sx={{ 
                            flex: 1,
                            bgcolor: 'primary.main',
                            '&:hover': {
                                bgcolor: 'primary.dark',
                            }
                        }}
                    >
                        Animate path
                    </Button>
                    <Button 
                        variant="contained" 
                        color="success" 
                        disabled={isSavePathDisabled()}
                        onClick={handleSavePath}
                        sx={{ 
                            flex: 1,
                            bgcolor: 'success.main',
                            '&:hover': {
                                bgcolor: 'success.dark',
                            }
                        }}
                    >
                        Save path
                    </Button>
                </Box>
            </Box>
            <Snackbar
                open={showSuccessMessage}
                autoHideDuration={3000}
                onClose={handleCloseSnackbar}
                anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            >
                <Alert onClose={handleCloseSnackbar} severity="success" sx={{ width: '100%' }}>
                    Path has been saved successfully
                </Alert>
            </Snackbar>
        </FormGroup>
    );
}
