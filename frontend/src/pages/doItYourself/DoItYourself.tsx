import { useState, useEffect, useRef } from "react";
import { Box, Card, CardContent, Grid, Typography, Button, useTheme, useMediaQuery, Tooltip, IconButton, Collapse } from "@mui/material";
import Board from "../../components/Board.tsx";
import { Piece, RotatedPiece } from "../../proto/solver/v1/solver.ts";
import PiecePalette from "./PiecePalette.tsx";
import DraggablePiece from "./DraggablePiece.tsx";
import { generateRandomPieces } from "./puzzleGenerator.ts";
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import InfoIcon from '@mui/icons-material/Info';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

function DoItYourself() {
    const theme = useTheme();
    const isLargeScreen = useMediaQuery(theme.breakpoints.up('lg'));
    
    // UI state
    const [howToPlayOpen, setHowToPlayOpen] = useState(true);
    
    // Puzzle state
    const [gridSize, setGridSize] = useState<3 | 4 | 5>(4);
    const [pieces, setPieces] = useState<Piece[]>([]);
    const [board, setBoard] = useState<(RotatedPiece | null)[]>(Array(16).fill(null)); // Default 4x4
    const [availablePieces, setAvailablePieces] = useState<RotatedPiece[]>([]);
    const [originalPieces, setOriginalPieces] = useState<Piece[]>([]);
    
    // Timer state
    const [isTimerRunning, setIsTimerRunning] = useState(false);
    const [elapsedTime, setElapsedTime] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    
    // Toggle how to play section
    const toggleHowToPlay = () => {
        setHowToPlayOpen(!howToPlayOpen);
    };
    
    // Generate a new puzzle
    const generateNewPuzzle = () => {
        // Stop timer if running
        if (isTimerRunning) {
            stopTimer();
        }
        
        // Reset timer
        setElapsedTime(0);
        
        // Generate random pieces for the puzzle
        const newPieces = generateRandomPieces(gridSize * gridSize);
        setPieces(newPieces);
        setOriginalPieces(newPieces); // Save original pieces for reset
        
        // Create empty board
        setBoard(Array(gridSize * gridSize).fill(null));
        
        // Create available pieces
        const newAvailablePieces = newPieces.map((piece, index) => ({
            piece: piece,
            rotation: 0,
            index: index
        }));
        setAvailablePieces(newAvailablePieces);
        
        // Don't start the timer automatically - user will click start button
    };
    
    // Reset the current puzzle without generating new pieces
    const resetPuzzle = () => {
        // Stop timer if running
        if (isTimerRunning) {
            stopTimer();
        }
        
        // Reset timer
        setElapsedTime(0);
        
        // Create empty board
        setBoard(Array(gridSize * gridSize).fill(null));
        
        // Restore available pieces from original pieces
        const restoredPieces = originalPieces.map((piece, index) => ({
            piece: piece,
            rotation: 0,
            index: index
        }));
        setAvailablePieces(restoredPieces);
        
        // Don't start the timer automatically
    };
    
    // Update grid size and generate a new puzzle
    const handleGridSizeChange = (newSize: 3 | 4 | 5) => {
        // Stop timer if running
        if (isTimerRunning) {
            stopTimer();
        }
        
        // Update the grid size
        setGridSize(newSize);
        
        // Update board size immediately
        setBoard(Array(newSize * newSize).fill(null));
        
        // Generate new puzzle with the new size
        const newPieces = generateRandomPieces(newSize * newSize);
        setPieces(newPieces);
        setOriginalPieces(newPieces);
        
        // Reset timer
        setElapsedTime(0);
        
        // Create available pieces
        const newAvailablePieces = newPieces.map((piece, index) => ({
            piece: piece,
            rotation: 0,
            index: index
        }));
        setAvailablePieces(newAvailablePieces);
    };
    
    // Timer functions
    const startTimer = () => {
        setIsTimerRunning(true);
        timerRef.current = setInterval(() => {
            setElapsedTime(prev => prev + 1);
        }, 1000);
    };
    
    const stopTimer = () => {
        if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
        setIsTimerRunning(false);
    };
    
    // Format time as mm:ss
    const formatTime = (seconds: number): string => {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    };
    
    // Handle piece drop on board
    const handlePieceDrop = (pieceIndex: number, boardIndex: number, rotation: number) => {
        // If the boardIndex already has a piece, don't allow drop
        if (board[boardIndex] !== null) return;
        
        // Find the piece in available pieces
        const pieceToPlace = availablePieces.find(p => p.index === pieceIndex);
        if (!pieceToPlace) return;
        
        // Update the board
        const newBoard = [...board];
        newBoard[boardIndex] = {
            ...pieceToPlace,
            rotation
        };
        setBoard(newBoard);
        
        // Remove from available pieces
        const newAvailablePieces = availablePieces.filter(p => p.index !== pieceIndex);
        setAvailablePieces(newAvailablePieces);
        
        // Check if puzzle is complete
        if (newAvailablePieces.length === 0) {
            stopTimer();
            // Could add victory celebration here
        }
    };
    
    // Handle removing a piece from the board
    const handleRemovePiece = (boardIndex: number) => {
        // Get the piece from the board
        const pieceToRemove = board[boardIndex];
        if (!pieceToRemove) return;
        
        // Create a copy of the board and remove the piece
        const newBoard = [...board];
        newBoard[boardIndex] = null;
        setBoard(newBoard);
        
        // Add the piece back to available pieces
        // Reset rotation to 0
        const removedPiece = {
            ...pieceToRemove,
            rotation: 0
        };
        setAvailablePieces([...availablePieces, removedPiece]);
    };
    
    // Handle rotation of a piece on the board
    const handleBoardPieceRotate = (pieceIndex: number, newRotation: number) => {
        const newBoard = [...board];
        const piece = newBoard[pieceIndex];
        if (piece) {
            newBoard[pieceIndex] = {
                ...piece,
                rotation: newRotation
            };
            setBoard(newBoard);
        }
    };
    
    // Generate a puzzle on component mount but don't start timer
    useEffect(() => {
        generateNewPuzzle();
    }, []);
    
    // Clean up timer on unmount
    useEffect(() => {
        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
        };
    }, []);

    return (
        <Box 
            sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                p: 2,
            }}
        >
            <Grid 
                container 
                spacing={3} 
                sx={{ 
                    flex: 1,
                    minHeight: 0,
                    width: '100%',
                    m: 0,
                    height: '100%', // Ensure grid takes full height
                    display: 'flex', // Use flex to align children
                }}
            >
                {/* Board Display - Fixed Position */}
                <Grid 
                    item 
                    xs={12} 
                    lg={7} 
                    sx={{
                        height: isLargeScreen ? '100%' : 'auto',
                        minHeight: 0,
                        p: '12px !important',
                    }}
                >
                    <Card 
                        elevation={0}
                        sx={{ 
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            bgcolor: 'background.paper',
                            border: '1px solid',
                            borderColor: 'divider',
                            position: isLargeScreen ? 'sticky' : 'static',
                            top: 16,
                        }}
                    >
                        <CardContent 
                            sx={{ 
                                flex: 1,
                                p: 3,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                minHeight: 0,
                                '&:last-child': { pb: 3 },
                            }}
                        >
                            <Box 
                                sx={{
                                    width: '100%',
                                    height: '100%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                <Box
                                    sx={{
                                        width: 'min(100%, calc(100vh - 250px))',
                                        aspectRatio: '1/1',
                                    }}
                                >
                                    {/* Custom board that can accept drops and handle rotations */}
                                    <DraggablePiece.BoardDropZone 
                                        gridSize={gridSize}
                                        board={board}
                                        onDrop={handlePieceDrop}
                                        onRotate={handleBoardPieceRotate}
                                        onRemove={handleRemovePiece}
                                    />
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>

                {/* Controls - Scrollable */}
                <Grid 
                    item 
                    xs={12} 
                    lg={5} 
                    sx={{ 
                        height: isLargeScreen ? '100%' : 'auto',
                        minHeight: 0,
                        p: '12px !important',
                        display: 'flex',
                    }}
                >
                    <Card 
                        elevation={0}
                        sx={{ 
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            bgcolor: 'background.paper',
                            border: '1px solid',
                            borderColor: 'divider',
                            width: '100%',
                            overflow: 'hidden', // Prevent overflow from the card
                        }}
                    >
                        <CardContent 
                            sx={{ 
                                p: 3,
                                flex: 1,
                                overflow: 'auto', // Make this container scrollable
                                '&:last-child': { pb: 3 },
                                display: 'flex',
                                flexDirection: 'column',
                                minHeight: 0, // Essential for flexbox scrolling in Firefox
                                maxHeight: isLargeScreen ? 'calc(100vh - 185px)' : 'auto', // Finer adjustment for perfect alignment
                            }}
                        >
                            <Typography 
                                variant="h5" 
                                component="h1" 
                                gutterBottom
                                sx={{ 
                                    mb: 3,
                                    fontWeight: 600,
                                    color: 'text.primary'
                                }}
                            >
                                Do It Yourself
                            </Typography>
                            
                            {/* Puzzle Controls */}
                            <Box sx={{ mb: 3, flexShrink: 0 }}>
                                {/* Grid Size with buttons aligned to the right */}
                                <Box sx={{ 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    justifyContent: 'space-between',
                                    mb: 2
                                }}>
                                    <Typography variant="subtitle1" sx={{ m: 0 }}>
                                        Grid Size
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 1 }}>
                                        <Button 
                                            variant={gridSize === 3 ? "contained" : "outlined"} 
                                            onClick={() => handleGridSizeChange(3)}
                                            size="small"
                                        >
                                            3x3
                                        </Button>
                                        <Button 
                                            variant={gridSize === 4 ? "contained" : "outlined"} 
                                            onClick={() => handleGridSizeChange(4)}
                                            size="small"
                                        >
                                            4x4
                                        </Button>
                                        <Button 
                                            variant={gridSize === 5 ? "contained" : "outlined"} 
                                            onClick={() => handleGridSizeChange(5)}
                                            size="small"
                                        >
                                            5x5
                                        </Button>
                                    </Box>
                                </Box>
                                
                                <Button 
                                    variant="contained" 
                                    fullWidth 
                                    onClick={generateNewPuzzle}
                                    sx={{ mb: 2 }}
                                >
                                    Generate New Puzzle
                                </Button>
                                
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h6" sx={{ flexGrow: 1 }}>
                                        Time: {formatTime(elapsedTime)}
                                    </Typography>
                                    
                                    <Box sx={{ display: 'flex', gap: 1 }}>
                                        <Button 
                                            variant="outlined" 
                                            color={isTimerRunning ? "error" : "success"}
                                            onClick={isTimerRunning ? stopTimer : startTimer}
                                            startIcon={isTimerRunning ? <StopIcon /> : <PlayArrowIcon />}
                                        >
                                            {isTimerRunning ? "Stop" : "Start"}
                                        </Button>
                                        
                                        <Button 
                                            variant="outlined" 
                                            color="primary"
                                            onClick={resetPuzzle}
                                            startIcon={<RestartAltIcon />}
                                            disabled={originalPieces.length === 0}
                                        >
                                            Reset
                                        </Button>
                                    </Box>
                                </Box>
                                
                                {/* Collapsible How to Play section */}
                                <Box 
                                    sx={{ 
                                        mb: 2,
                                        border: '1px solid',
                                        borderColor: 'divider',
                                        borderRadius: 1,
                                        overflow: 'hidden',
                                    }}
                                >
                                    <Box
                                        sx={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            p: 1.5,
                                            bgcolor: 'background.default',
                                            cursor: 'pointer',
                                        }}
                                        onClick={toggleHowToPlay}
                                    >
                                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                            <HelpOutlineIcon sx={{ mr: 1, color: 'primary.main' }} />
                                            <Typography variant="subtitle2" fontWeight="bold">
                                                How to play
                                            </Typography>
                                        </Box>
                                        <IconButton size="small" edge="end">
                                            {howToPlayOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                                        </IconButton>
                                    </Box>
                                    
                                    <Collapse in={howToPlayOpen}>
                                        <Box sx={{ p: 2, bgcolor: 'background.paper' }}>
                                            <Box 
                                                sx={{ 
                                                    display: 'flex', 
                                                    alignItems: 'center', 
                                                    color: 'text.secondary',
                                                    mb: 1,
                                                }}
                                            >
                                                <InfoIcon fontSize="small" sx={{ mr: 1 }} />
                                                <Typography variant="body2">
                                                    Drag and drop pieces to place them on the board.
                                                </Typography>
                                            </Box>
                                            
                                            <Box 
                                                sx={{ 
                                                    display: 'flex', 
                                                    alignItems: 'center', 
                                                    color: 'text.secondary',
                                                    mb: 1,
                                                }}
                                            >
                                                <InfoIcon fontSize="small" sx={{ mr: 1 }} />
                                                <Typography variant="body2">
                                                    Right-click to rotate pieces.
                                                </Typography>
                                            </Box>
                                            
                                            <Box 
                                                sx={{ 
                                                    display: 'flex', 
                                                    alignItems: 'center', 
                                                    color: 'text.secondary',
                                                }}
                                            >
                                                <InfoIcon fontSize="small" sx={{ mr: 1 }} />
                                                <Typography variant="body2">
                                                    Click a placed piece to remove it from the board.
                                                </Typography>
                                            </Box>
                                        </Box>
                                    </Collapse>
                                </Box>
                            </Box>
                            
                            {/* Available Pieces - Make this part scrollable */}
                            <Typography variant="subtitle1" gutterBottom>
                                Available Pieces
                            </Typography>
                            <Box sx={{ 
                                flex: 1,
                                mt: 1,
                                minHeight: 0, // Important for proper flexbox behavior
                                overflow: 'visible', // Let parent handle scrolling
                                pb: 1,
                            }}>
                                <PiecePalette pieces={availablePieces} />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Box>
    );
}

export default DoItYourself; 