import {SyntheticEvent, useCallback, useState, useEffect} from 'react';
import {hintTemplatesState, pathsState} from "../requestForm/atoms.ts";
import {Autocomplete, Button, FormGroup, Slider, TextField, Typography, Dialog, DialogTitle, DialogContent, DialogActions} from "@mui/material";
import {useRecoilState} from "recoil";
import Box from "@mui/material/Box";
import {boardSizeState, DEFAULT_SELECTED_CELLS, selectedCellsState, selectedPathState, hintCellsState} from "./atom.ts";
import {convertPathToSelectedCells} from "./utils.ts";
import {BOARD_SIZE_DEFAULT, BOARD_SIZE_MAX, BOARD_SIZE_MIN, BOARD_SIZE_STEP} from "../../utils/Constants.tsx";
import {Path} from "../../utils/interface.tsx";
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteIcon from '@mui/icons-material/Delete';
import { calculateCellDelay } from "./animation.ts";

export const DisplayPathForm = () => {
    const [paths, setPaths] = useRecoilState(pathsState);
    const [hints, setHints] = useRecoilState(hintTemplatesState);
    // @ts-ignore - hintCells is used in resetGrid and handlePathChange
    const [hintCells, setHintCells] = useRecoilState(hintCellsState);

    // States used by path manager
    const [boardSize, setBoardSize] = useRecoilState(boardSizeState);
    const [selectedCells, setSelectedCells] = useRecoilState(selectedCellsState);
    const [selectedPath, setSelectedPath] = useRecoilState(selectedPathState);

    // Delete confirmation dialog
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

    // Animation states
    const [isAnimating, setIsAnimating] = useState(false);
    const [animationTimeout, setAnimationTimeout] = useState<NodeJS.Timeout | null>(null);

    const resetGrid = () => {
        setSelectedCells(DEFAULT_SELECTED_CELLS);
        setHintCells([]);
    }

    const handleDeletePath = () => {
        if (!selectedPath) return;

        // Remove the path from paths
        setPaths(paths.filter(path => path.label !== selectedPath.label));
        
        // Remove the corresponding hint template
        setHints(hints.filter(hint => hint.label !== selectedPath.label));
        
        // Reset the grid and selected path
        setSelectedPath(null);
        resetGrid();
        
        // Close the dialog
        setIsDeleteDialogOpen(false);
    }

    // ===== Animation ==== //
    const startAnimation = useCallback(() => {
        if (selectedCells.length <= 1 || isAnimating || !selectedPath) return;

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
    }, [selectedCells, isAnimating, selectedPath, setSelectedCells]);

    // Cleanup animation on unmount
    useEffect(() => {
        return () => {
            if (animationTimeout) {
                clearTimeout(animationTimeout);
            }
        };
    }, [animationTimeout]);

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
            
            // Find and set the corresponding hints
            const pathHints = hints.find(hint => hint.label === value.label);
            if (pathHints) {
                setHintCells(pathHints.pieceIndex);
            } else {
                setHintCells([]);
            }
        } else {
            setSelectedPath(null);
            resetGrid();
        }
    }

    const isAnimateDisabled = () => {
        return !selectedPath || selectedCells.length <= 1 || isAnimating;
    };

    const isDeleteDisabled = () => {
        return !selectedPath;
    };

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
                        variant="contained"
                        color="error" 
                        onClick={() => setIsDeleteDialogOpen(true)}
                        disabled={isDeleteDisabled()}
                        startIcon={<DeleteIcon />}
                        sx={{ 
                            flex: 1,
                            bgcolor: 'error.main',
                            '&:hover': {
                                bgcolor: 'error.dark',
                            }
                        }}
                    >
                        Delete Path
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
                </Box>
            </Box>

            {/* Delete Confirmation Dialog */}
            <Dialog
                open={isDeleteDialogOpen}
                onClose={() => setIsDeleteDialogOpen(false)}
                aria-labelledby="delete-dialog-title"
            >
                <DialogTitle id="delete-dialog-title">
                    Delete Path
                </DialogTitle>
                <DialogContent>
                    Are you sure you want to delete the path "{selectedPath?.label}"? This action cannot be undone.
                </DialogContent>
                <DialogActions>
                    <Button 
                        onClick={() => setIsDeleteDialogOpen(false)} 
                        color="primary"
                        variant="outlined"
                    >
                        Cancel
                    </Button>
                    <Button 
                        onClick={handleDeletePath} 
                        color="error" 
                        variant="contained"
                        sx={{ 
                            bgcolor: 'error.main',
                            '&:hover': {
                                bgcolor: 'error.dark',
                            }
                        }}
                    >
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>
        </FormGroup>
    );
}
